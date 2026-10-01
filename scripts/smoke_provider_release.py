"""Prove application provider extensions against installed artifacts offline.

Build the source wheel and source archive, rebuild a second wheel from that
archive outside the checkout, and install each wheel into fresh base,
``mcp``-extra and ``conformance``-extra environments. In every environment,
copy only the repository-owned fixture and probe files, run them with the
environment's interpreter and an isolated environment, and compare their
receipts with the oracle below. No child reaches an inference service or the
network. Every uv child names the cache that `uv_cache_args` selects.

The base environment also proves that the fakes import without pytest and that
the conformance kit refuses to import with an error naming its extra. The
``conformance`` environment requires the extra to add exactly pytest and
anyio, runs a provider test module against the installed kit with pytest and
requires every rule test to pass. The module runs nine
synchronous rules and six asynchronous rules.

Source: https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5851596904.
Repair: https://github.com/Alberto-Codes/judgevet/issues/205#issuecomment-5851983135.
Conformance: https://github.com/Alberto-Codes/judgevet/issues/241#issuecomment-5902293909.
Async conformance: https://github.com/Alberto-Codes/judgevet/issues/246.
Async scope rules: https://github.com/Alberto-Codes/judgevet/issues/251.
Anyio in the extra: https://github.com/Alberto-Codes/judgevet/issues/253.

Usage: ``uv run python scripts/smoke_provider_release.py``. Exit status is 0
only when all six environments pass.

Examples:
    ```python
    from scripts.smoke_provider_release import expected_checks

    assert "mcp_owned" in expected_checks(extra=True)
    ```

See Also:
    - [scripts.provider_artifact_check][]: In-environment identity probe.
    - [scripts.smoke_release][]: Build, venv and install helpers reused here.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from scripts.provider_artifact_check import (
    INFERENCE,
    ORIGINS_VARIABLE,
    SEED,
    check_origins,
    normalize,
)
from scripts.smoke_release import (
    build_child_env,
    build_wheel,
    create_venv,
    install_wheel,
    run_process,
    uv_cache_args,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "providers"
FIXTURE_FILES = (
    "provider_fixture.py",
    "cli_app.py",
    "mcp_app.py",
    "consumer_checks.py",
    "conformance_absent.py",
    "conformance_provider.py",
)
PROBE = ROOT / "scripts" / "provider_artifact_check.py"
CHILD_TIMEOUT = 600
CONFORMANCE_EXTRA = "conformance"
CONFORMANCE_REQUIRES = frozenset({"pytest", "anyio"})
KIT_MODULE = "judgevet.testing.conformance"
KIT_TESTS = "tests/fixtures/providers/conformance_provider.py"
KIT_RULES = 15
EXPECTED_ABSENT = {
    "receipt": "conformance-absent",
    "fakes": "FakeSystemOnePort",
    "pytest": False,
    "error": "ImportError",
    "extra_named": True,
}
_LOCALE = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")
_SYSTEM_PATH = "/usr/bin:/bin"

# --------------------------------------------------------------------------- #
# Oracle. These values restate the fixture contract independently, so a child
# that prints success without the exact behaviour fails here.
# --------------------------------------------------------------------------- #
STATE = {"claim": "Invoice 7 was paid", "ticket": 7}
MODEL = "app-model"
PAGE_1 = ["page-1", "image/png", "89504e470d0a1a0a666978747572652d706167652d31"]
PAGE_2 = ["page-2", "image/jpeg", "ffd8ff666978747572652d706167652d32"]
BINDINGS = {"support": ["page-2", "page-1"], "legible": ["page-1"]}
_OUTCOMES = {
    "supported": "supported",
    "contradicted": "contradicted",
    "insufficient_evidence": "insufficient evidence",
}
QUESTIONS_SEEN = {
    "support": ["choice", "Does the attached page support the claim?", _OUTCOMES],
    "legible": ["noul", "Is the attached page legible?", None],
    "quality": ["score", "Rate the scan quality.", ["poor", "fair", "good"]],
}
TEXT_FINDINGS = [
    ["support", "insufficient_evidence", 0.8],
    ["legible", "unlikely", 0.25],
    ["quality", "fair", 0.5],
]
MEDIA_FINDINGS = [
    ["support", "supported", 0.9],
    ["legible", "likely", 0.95],
    ["quality", "fair", 0.5],
]
INSUFFICIENT_FINDINGS = [
    ["support", "insufficient_evidence", 0.8],
    ["legible", "likely", 0.95],
    ["quality", "fair", 0.5],
]
POLICY_FAIL = [False, [["support", False], ["legible", False]]]
POLICY_PASS = [True, [["support", True], ["legible", True]]]
POLICY_INSUFFICIENT = [False, [["support", False], ["legible", True]]]


def _call(
    provider: str,
    operation: str = "text",
    images: list[list[str]] | None = None,
    bindings: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build one expected provider call observation.

    Args:
        provider: Provider identity that must receive the call.
        operation: ``text`` or ``media``.
        images: Expected ``[id, media type, bytes hex]`` in global order.
        bindings: Expected per-question references.

    Returns:
        Exact call summary the fixture must record.
    """
    return {
        "provider": provider,
        "operation": operation,
        "state": STATE,
        "questions": QUESTIONS_SEEN,
        "model": MODEL,
        "images": images or [],
        "bindings": dict(bindings or {}),
    }


def _lifecycle(provider: str, middle: tuple[str, ...] = ()) -> list[list[str]]:
    """Build owned-provider events: acquire, the middle events, then close.

    Args:
        provider: Owned provider identity.
        middle: Events between acquisition and close.

    Returns:
        Expected ``[event, provider]`` pairs.
    """
    events = [["acquire", provider]]
    events.extend([name, provider] for name in middle)
    return [*events, ["close", provider]]


def _owned(provider: str, error: str | None, events: list[list[str]]) -> dict:
    """Build an expected owned-factory observation.

    Args:
        provider: Owned provider identity.
        error: Expected failure class, or None.
        events: Expected lifecycle events.

    Returns:
        Expected observation.
    """
    models = [] if error else [f"{MODEL}@{provider}"]
    return {"error": error, "models": models, "fallback_calls": 0, "events": events}


_HOSTED_QUESTIONS = {
    "support": {
        "type": "choice",
        "instructions": QUESTIONS_SEEN["support"][1],
        "criteria": _OUTCOMES,
    },
    "legible": {"type": "noul", "instructions": QUESTIONS_SEEN["legible"][1]},
    "quality": {
        "type": "score",
        "instructions": QUESTIONS_SEEN["quality"][1],
        "criteria": ["poor", "fair", "good"],
    },
}
EXPECTED_LIBRARY: dict[str, Any] = {
    "library_text": {
        "model": f"{MODEL}@borrowed-library",
        "usage": [17, 5],
        "findings": TEXT_FINDINGS,
        "policy": POLICY_FAIL,
        "calls": [_call("borrowed-library")],
        "closed": 0,
        "events": [["call", "borrowed-library"]],
    },
    "library_media": {
        "model": f"{MODEL}@borrowed-library",
        "usage": [None, None],
        "findings": MEDIA_FINDINGS,
        "policy": POLICY_PASS,
        "calls": [_call("borrowed-library", "media", [PAGE_1, PAGE_2], BINDINGS)],
        "events": [["call", "borrowed-library"]],
    },
    "library_insufficient": {
        "model": f"{MODEL}@borrowed-library",
        "usage": [None, None],
        "findings": INSUFFICIENT_FINDINGS,
        "policy": POLICY_INSUFFICIENT,
        "calls": [
            _call("borrowed-library", "media", [PAGE_1], {"legible": ["page-1"]})
        ],
        "events": [["call", "borrowed-library"]],
    },
    "library_unsupported": {
        "errors": ["ProviderCapabilityError", "ProviderCapabilityError"],
        "calls": [0, 0],
        "events": [],
    },
    "library_owned": _owned(
        "owned-library", None, _lifecycle("owned-library", ("call",))
    ),
    "library_call_failure": _owned(
        "failing-library",
        "ProviderTransportError",
        _lifecycle("failing-library", ("call",)),
    ),
    "library_setup_failure": _owned(
        "setup-library",
        "ProviderUnavailableError",
        [["acquire", "setup-library"], ["rollback", "setup-library"]],
    ),
    "library_invalid_port": _owned(
        "invalid-library", "ProviderUnavailableError", _lifecycle("invalid-library")
    ),
    "library_hosted": {
        "model": "jev-hosted-fixture",
        "usage": [3, 2],
        "findings": [
            ["support", "supported", 0.7],
            ["legible", "likely", 0.9],
            ["quality", "good", 1.0],
        ],
        "requests": 1,
        "method": "POST",
        "url": "https://api.typesafe.ai/v1/systemone",
        "credential": True,
        "body": {"state": STATE, "questions": _HOSTED_QUESTIONS, "model": MODEL},
    },
    "library_provenance": {
        "ids": ["page-1", "page-2"],
        "by_question": BINDINGS,
        "revisions": ["review-prompt-1", "borrowed-library", None],
        "stable": True,
        "evidence_sensitive": True,
        "request_unchanged": True,
        "digests_distinct": True,
        "raw_absent": True,
    },
}
TEXT_USAGE = {"input_tokens": 17, "output_tokens": 5}
UNKNOWN_USAGE = {"input_tokens": None, "output_tokens": None}
TEXT_ANSWERS = [
    ["support", "choice", "insufficient_evidence", 0.8],
    ["legible", "noul", 0.25, None],
    ["quality", "score", 0.5, 0.6],
]
MEDIA_ANSWERS = [
    ["support", "choice", "supported", 0.9],
    ["legible", "noul", 0.95, None],
    ["quality", "score", 0.5, 0.6],
]
RENDERED_PASS = ["pass", [["support", True], ["legible", True]]]
RENDERED_FAIL = ["fail", [["support", False], ["legible", False]]]


def _rendered(provider: str, media: bool, policy: list | None = None) -> dict:
    """Build an expected rendered CLI or MCP envelope summary.

    Args:
        provider: Provider identity in the resolved model.
        media: Whether the media answers and unknown usage are expected.
        policy: Expected rendered policy decision, if any.

    Returns:
        Expected summary.
    """
    result: dict[str, Any] = {
        "model": f"{MODEL}@{provider}",
        "usage": UNKNOWN_USAGE if media else TEXT_USAGE,
        "answers": MEDIA_ANSWERS if media else TEXT_ANSWERS,
    }
    if policy is not None:
        result["policy"] = policy
    return result


def _media_call(provider: str) -> dict[str, Any]:
    """Build the expected two-image call for one provider.

    Args:
        provider: Provider identity.

    Returns:
        Exact media call summary.
    """
    return _call(provider, "media", [PAGE_1, PAGE_2], BINDINGS)


_OWNED_CLI = _lifecycle("owned-cli", ("call",))
EXPECTED_PROCESS: dict[str, Any] = {
    "network": {"errors": ["NetworkBlockedError", "NetworkBlockedError"]},
    "cli_text_borrowed": {
        "code": 0,
        "output": _rendered("borrowed-cli", media=False),
        "error": "",
        "calls": [_call("borrowed-cli")],
        "events": [["call", "borrowed-cli"], ["borrowed-exit", 0]],
    },
    "cli_media_owned": {
        "code": 0,
        "output": _rendered("owned-cli", media=True, policy=RENDERED_PASS),
        "error": "",
        "calls": [_media_call("owned-cli")],
        "events": _OWNED_CLI,
    },
    "cli_insufficient": {
        "code": 3,
        "output": _rendered("owned-cli", media=False, policy=RENDERED_FAIL),
        "error": "",
        "calls": [_call("owned-cli")],
        "events": _OWNED_CLI,
    },
    "cli_call_failure": {
        "code": 1,
        "output": None,
        "error": '{"error": "fixture transport failure"}',
        "calls": [_call("failing-cli")],
        "events": _lifecycle("failing-cli", ("call",)),
    },
    "cli_unsupported": {
        "code": 1,
        "output": None,
        "error": '{"error": "Provider must expose callable media methods"}',
        "calls": [],
        "events": [["borrowed-exit", 0]],
    },
}
EXPECTED_BASE: dict[str, Any] = {
    "mcp_absent": {
        "code": 2,
        "error": "judgevet-mcp: install judgevet[mcp] to use this command",
        "mcp_spec": False,
        "calls": [],
        "events": [],
    },
}
_TOOLS = ["ask_choice", "ask_noul", "ask_score", "evaluate_policy"]


def _tool(provider: str, media: bool, policy: list) -> dict[str, Any]:
    """Build an expected successful MCP tool result summary.

    Args:
        provider: Provider identity in the resolved model.
        media: Whether the media answers and unknown usage are expected.
        policy: Expected rendered policy decision.

    Returns:
        Expected tool summary.
    """
    data = _rendered(provider, media=media, policy=policy)
    return {"error": False, "text_matches": True, "data": data}


EXPECTED_EXTRA: dict[str, Any] = {
    "mcp_owned": {
        "tools": _TOOLS,
        "media": _tool("owned-mcp", True, RENDERED_PASS),
        "text": _tool("owned-mcp", False, RENDERED_FAIL),
        "code": 0,
        "calls": [_media_call("owned-mcp"), _call("owned-mcp")],
        "events": _lifecycle("owned-mcp", ("call", "call")),
    },
    "mcp_text_only": {
        "tools": _TOOLS,
        "media": {
            "error": True,
            "text": ["ProviderCapabilityError: media evaluation failed"],
        },
        "text": _tool("text-only-mcp", False, RENDERED_FAIL),
        "code": 0,
        "calls": [_call("text-only-mcp")],
        "events": [["call", "text-only-mcp"], ["borrowed-exit", 0]],
    },
}
EXPECTED_EXTRA |= {
    f"mcp_sdk_{name.removeprefix('mcp_')}": {
        key: value for key, value in check.items() if key != "code"
    }
    for name, check in EXPECTED_EXTRA.items()
}
_CLI_CHILDREN = tuple(name for name in EXPECTED_PROCESS if name.startswith("cli_"))
BLOCKED = {"errors": ["NetworkBlockedError", "NetworkBlockedError"]}


def expected_children(*, extra: bool) -> tuple[str, ...]:
    """Name every runtime child whose origin receipt must be recorded.

    Args:
        extra: Whether the environment installed the ``mcp`` extra.

    Returns:
        Child labels: CLI wrappers, then MCP servers or the refused start.
    """
    servers = tuple(name for name in EXPECTED_EXTRA) if extra else ("mcp_absent",)
    return _CLI_CHILDREN + servers


def expected_checks(*, extra: bool) -> dict[str, Any]:
    """Return every check the consumer receipt must contain with exact values.

    Args:
        extra: Whether the environment installed the ``mcp`` extra.

    Returns:
        Check names mapped to their exact expected observations.
    """
    specific = EXPECTED_EXTRA if extra else EXPECTED_BASE
    return EXPECTED_LIBRARY | EXPECTED_PROCESS | specific


def mismatches(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    """Name expected checks whose observation is missing or different.

    Args:
        observed: Observations keyed by check name.
        expected: Exact expected observations keyed by check name.

    Returns:
        Sorted names of failed checks.
    """
    return sorted(
        name for name, value in expected.items() if observed.get(name) != value
    )


# --------------------------------------------------------------------------- #
# Receipt validation.
# --------------------------------------------------------------------------- #
def parse_receipt(completed: subprocess.CompletedProcess[str], kind: str) -> dict:
    """Require a successful child and its final JSON receipt line.

    Args:
        completed: Finished child process.
        kind: Expected ``receipt`` value.

    Returns:
        The decoded receipt.

    Raises:
        RuntimeError: The child failed or printed no matching receipt.
    """
    if completed.returncode != 0:
        tail = completed.stderr.strip().splitlines()[-5:]
        raise RuntimeError(f"{kind} child exited {completed.returncode}: {tail}")
    lines = completed.stdout.strip().splitlines()
    try:
        receipt = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        receipt = None
    if not isinstance(receipt, dict) or receipt.get("receipt") != kind:
        raise RuntimeError(f"{kind} child printed no receipt")
    return receipt


def closure(
    root: str,
    extras: Sequence[str],
    graph: Mapping[str, Sequence[str]],
    environment: Mapping[str, str],
) -> set[str]:
    """Collect every applicable dependency of a root, installed or not.

    PEP 508 markers are evaluated for the tested interpreter with ``packaging``.
    A requirement's extras apply to that dependency; ``extra`` markers are
    evaluated once per selected extra, or with an empty extra when none is.

    Args:
        root: Normalized root distribution.
        extras: Extras selected for the root.
        graph: Installed normalized names mapped to requirement strings.
        environment: The tested interpreter's marker environment.

    Returns:
        Applicable names, including nodes absent from the installation.
    """
    visited: set[tuple[str, frozenset[str]]] = set()
    pending = [(canonicalize_name(root), frozenset(map(canonicalize_name, extras)))]
    while pending:
        name, selected = pending.pop()
        if (name, selected) in visited:
            continue
        visited.add((name, selected))
        contexts = [dict(environment, extra=item) for item in sorted(selected)]
        contexts = contexts or [dict(environment, extra="")]
        for text in graph.get(name, ()):
            requirement = Requirement(text)
            marker = requirement.marker
            if marker is None or any(marker.evaluate(env) for env in contexts):
                child_extras = frozenset(map(canonicalize_name, requirement.extras))
                pending.append((canonicalize_name(requirement.name), child_extras))
    return {name for name, _ in visited}


def check_inventory(
    graph: Mapping[str, Sequence[str]],
    environment: Mapping[str, str],
    *,
    extra: bool,
) -> None:
    """Require exactly the declared dependency closure and no inference runtime.

    Args:
        graph: Installed normalized names mapped to requirement strings.
        environment: The tested interpreter's marker environment.
        extra: Whether the environment installed the ``mcp`` extra.

    Raises:
        RuntimeError: A dependency is missing, undeclared or forbidden.
    """
    installed = {canonicalize_name(name) for name in graph} - SEED
    expected = closure("judgevet", ("mcp",) if extra else (), graph, environment)
    if installed != expected:
        undeclared, missing = sorted(installed - expected), sorted(expected - installed)
        raise RuntimeError(
            "Installed distributions differ from the declared closure: "
            f"undeclared={undeclared} missing={missing}"
        )
    if extra != ("mcp" in installed):
        raise RuntimeError("MCP presence does not match the selected install")
    if installed & INFERENCE:
        raise RuntimeError("An inference runtime is installed")


def _active(
    requires: Sequence[str], environment: Mapping[str, str], extra: str
) -> set[str]:
    """Name the requirements whose markers hold for one selected extra.

    Args:
        requires: Raw ``Requires-Dist`` strings of one distribution.
        environment: The tested interpreter's marker environment.
        extra: The selected extra, or an empty string for none.

    Returns:
        Normalized names of the applicable requirements.
    """
    context = dict(environment, extra=extra)
    names = set()
    for text in requires:
        requirement = Requirement(text)
        marker = requirement.marker
        if marker is None or marker.evaluate(context):
            names.add(canonicalize_name(requirement.name))
    return names


def check_conformance_metadata(
    requires: Sequence[str], environment: Mapping[str, str]
) -> None:
    """Require pytest and anyio only behind the ``conformance`` extra.

    The extra must add exactly pytest and anyio, the two distributions the
    kit imports. Source: https://github.com/Alberto-Codes/judgevet/issues/253.

    Args:
        requires: The installed judgevet ``Requires-Dist`` strings.
        environment: The tested interpreter's marker environment.

    Raises:
        RuntimeError: The base install requires pytest or anyio directly, or
            the extra adds other than exactly pytest and anyio.
    """
    base = _active(requires, environment, "")
    if base & CONFORMANCE_REQUIRES:
        direct = sorted(base & CONFORMANCE_REQUIRES)
        raise RuntimeError(f"The base install requires {direct}")
    added = _active(requires, environment, CONFORMANCE_EXTRA) - base
    if added != CONFORMANCE_REQUIRES:
        raise RuntimeError(f"The conformance extra adds {sorted(added)}")


def check_conformance_inventory(
    graph: Mapping[str, Sequence[str]], environment: Mapping[str, str]
) -> None:
    """Require the ``conformance`` closure, pytest, anyio and no inference runtime.

    Args:
        graph: Installed normalized names mapped to requirement strings.
        environment: The tested interpreter's marker environment.

    Raises:
        RuntimeError: A dependency is missing, undeclared or forbidden.
    """
    installed = {canonicalize_name(name) for name in graph} - SEED
    expected = closure("judgevet", (CONFORMANCE_EXTRA,), graph, environment)
    if installed != expected:
        undeclared, missing = sorted(installed - expected), sorted(expected - installed)
        raise RuntimeError(
            "Installed distributions differ from the conformance closure: "
            f"undeclared={undeclared} missing={missing}"
        )
    if not installed >= CONFORMANCE_REQUIRES or "mcp" in installed:
        raise RuntimeError("The conformance install does not match its extra")
    if installed & INFERENCE:
        raise RuntimeError("An inference runtime is installed")


def validate_identity(
    receipt: Mapping[str, Any],
    version: str,
    env_dir: Path,
    checkout: Path,
    *,
    extra: bool,
) -> None:
    """Validate one environment's identity receipt against the artifact.

    Args:
        receipt: Decoded identity receipt.
        version: Version recorded in the artifacts.
        env_dir: The environment directory.
        checkout: Repository checkout.
        extra: Whether the environment installed the ``mcp`` extra.

    Raises:
        RuntimeError: Any identity, typing, origin, inventory or
            conformance-extra metadata claim fails.
    """
    if receipt.get("receipt") != "provider-identity":
        raise RuntimeError("Wrong identity receipt")
    if receipt.get("version") != version or receipt.get("metadata_version") != version:
        raise RuntimeError("Installed version differs from the artifact")
    if receipt.get("py_typed") is not True:
        raise RuntimeError("Installed py.typed marker is missing")
    purelib = Path(str(receipt.get("purelib")))
    if not purelib.resolve().is_relative_to(env_dir.resolve()):
        raise RuntimeError("site-packages is outside the environment")
    check_origins(receipt.get("origins") or {}, purelib, checkout)
    if receipt.get("network") != BLOCKED or receipt.get("preimport") != []:
        raise RuntimeError("The identity process was not guarded before import")
    distributions = {
        normalize(name): value for name, value in dict(receipt["distributions"]).items()
    }
    if distributions.get("judgevet", {}).get("version") != version:
        raise RuntimeError("Dependency inventory lacks the installed artifact")
    graph = {name: value["requires"] for name, value in distributions.items()}
    check_inventory(graph, receipt["environment"], extra=extra)
    check_conformance_metadata(graph["judgevet"], receipt["environment"])
    if extra != receipt.get("mcp_spec"):
        raise RuntimeError("MCP presence differs from the selected install")


def validate_children(
    consumer: Mapping[str, Any], purelib: Path, checkout: Path, *, extra: bool
) -> None:
    """Validate origin maps and network guards from every runtime child.

    Args:
        consumer: Consumer receipt with ``origins`` and ``children``.
        purelib: The environment's site-packages.
        checkout: Repository checkout.
        extra: Whether the environment installed the ``mcp`` extra.

    Raises:
        RuntimeError: A child is missing, unguarded or loaded elsewhere.
    """
    check_origins(consumer.get("origins") or {}, purelib, checkout)
    children = consumer.get("children")
    if not isinstance(children, dict) or set(children) != set(
        expected_children(extra=extra)
    ):
        raise RuntimeError("Child origin receipts differ from the expected children")
    for label, child in children.items():
        if child.get("network") != BLOCKED or child.get("preimport") != []:
            raise RuntimeError(f"Child {label} was not guarded before import")
        check_origins(child.get("origins") or {}, purelib, checkout)


def environment_receipt(
    label: str,
    kind: str,
    digest: str,
    identity: Mapping[str, Any],
    consumer: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the printed receipt with actual module-to-file maps.

    Args:
        label: Artifact label.
        kind: ``base`` or ``mcp``.
        digest: Installed wheel SHA-256.
        identity: Validated identity receipt.
        consumer: Validated consumer receipt.

    Returns:
        Bounded receipt with site-packages and every recorded origin map.
    """
    return {
        "receipt": "provider-environment",
        "wheel": label,
        "kind": kind,
        "wheel_sha256": digest,
        "version": identity["version"],
        "purelib": identity["purelib"],
        "dependencies": {
            name: value["version"]
            for name, value in sorted(dict(identity["distributions"]).items())
        },
        "identity_origins": identity["origins"],
        "consumer_origins": consumer["origins"],
        "child_origins": {
            name: child["origins"] for name, child in consumer["children"].items()
        },
        "checks": sorted(consumer.get("checks", {})),
    }


def validate_consumer(receipt: Mapping[str, Any], *, extra: bool) -> None:
    """Compare every consumer observation with the oracle.

    Args:
        receipt: Decoded consumer receipt.
        extra: Whether the environment installed the ``mcp`` extra.

    Raises:
        RuntimeError: A check is missing, unexpected or different.
    """
    if receipt.get("receipt") != "provider-consumer":
        raise RuntimeError("Wrong consumer receipt")
    checks = receipt.get("checks")
    expected = expected_checks(extra=extra)
    if not isinstance(checks, dict) or set(checks) != set(expected):
        raise RuntimeError("Consumer checks differ from the expected matrix")
    failed = mismatches(checks, expected)
    if failed:
        raise RuntimeError(f"Consumer observations differ: {failed}")


# --------------------------------------------------------------------------- #
# Artifacts and environments.
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    """Hash a file.

    Args:
        path: File to hash.

    Returns:
        Hex SHA-256 digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_outside(path: Path, checkout: Path) -> None:
    """Refuse a working path inside the checkout.

    Args:
        path: Proposed temporary path.
        checkout: Repository checkout.

    Raises:
        RuntimeError: The path is inside the checkout.
    """
    if path.resolve().is_relative_to(checkout.resolve()):
        raise RuntimeError("Temporary environments must be outside the checkout")


def _field(text: str, name: str) -> str | None:
    """Read one core metadata header.

    Args:
        text: Metadata text.
        name: Header name.

    Returns:
        Header value, or None.
    """
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key == name:
            return value.strip()
    return None


def _wheel_facts(wheel: Path) -> tuple[str | None, bool]:
    """Read a wheel's metadata version and typing marker presence.

    Args:
        wheel: Wheel archive.

    Returns:
        Metadata version and whether ``judgevet/py.typed`` is packaged.
    """
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = [n for n in names if n.endswith(".dist-info/METADATA")]
        text = archive.read(metadata[0]).decode() if len(metadata) == 1 else ""
    return _field(text, "Version"), "judgevet/py.typed" in names


def artifact_version(source: Path, sdist: Path, rebuilt: Path) -> str:
    """Require one version across names and metadata, and packaged typing.

    Args:
        source: Wheel built from the checkout.
        sdist: Source archive.
        rebuilt: Wheel rebuilt from the source archive.

    Returns:
        The common version.

    Raises:
        RuntimeError: Versions disagree or a wheel lacks ``py.typed``.
    """
    versions = set()
    for wheel in (source, rebuilt):
        metadata, typed = _wheel_facts(wheel)
        if not typed:
            raise RuntimeError("A wheel lacks judgevet/py.typed")
        versions |= {metadata, wheel.name.split("-")[1]}
    stem = sdist.name.removesuffix(".tar.gz")
    with tarfile.open(sdist) as archive:
        member = archive.extractfile(f"{stem}/PKG-INFO")
        info = member.read().decode() if member is not None else ""
    versions |= {_field(info, "Version"), stem.split("-")[1]}
    if len(versions) != 1 or None in versions:
        raise RuntimeError("Artifact versions disagree")
    return str(versions.pop())


def rebuild_from_sdist(sdist: Path, out_dir: Path, workdir: Path) -> Path:
    """Build a wheel from the source archive outside the checkout.

    The build uses the uv cache that `uv_cache_args` names.

    Args:
        sdist: Source archive.
        out_dir: Fresh output directory.
        workdir: Working directory outside the checkout.

    Returns:
        The rebuilt wheel.

    Raises:
        RuntimeError: uv is absent, the build fails or yields other than one wheel.
    """
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv not found on PATH")
    command = [
        uv,
        "build",
        "--wheel",
        *uv_cache_args(),
        "--out-dir",
        str(out_dir),
        str(sdist),
    ]
    environment = {k: v for k, v in build_child_env().items() if k != "VIRTUAL_ENV"}
    result = run_process(command, environment, workdir, CHILD_TIMEOUT)
    wheels = sorted(out_dir.glob("*.whl"))
    if result.returncode != 0 or len(wheels) != 1:
        raise RuntimeError(f"sdist wheel build failed: {result.stderr[-2000:]}")
    return wheels[0]


def consumer_env(workdir: Path, python: Path) -> dict[str, str]:
    """Build an allowlisted consumer environment with isolated configuration.

    Only locale variables are inherited. No import path, virtual environment,
    credential or configuration variable passes through.

    Args:
        workdir: Consumer working directory.
        python: Environment interpreter.

    Returns:
        Child environment.
    """
    inherited = build_child_env()
    env = {name: inherited[name] for name in _LOCALE if name in inherited}
    home = workdir / "home"
    env |= {
        "PATH": f"{python.parent}:{_SYSTEM_PATH}",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "TMPDIR": str(workdir / "tmp"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
    }
    return env


def stage(workdir: Path) -> None:
    """Copy only the repository-owned fixture and probe files.

    Args:
        workdir: Consumer working directory outside the checkout.
    """
    package = workdir / "tests" / "fixtures" / "providers"
    package.mkdir(parents=True)
    for directory in (workdir / "tests", package.parent, package):
        (directory / "__init__.py").write_text("")
    for name in FIXTURE_FILES:
        shutil.copyfile(FIXTURES / name, package / name)
    shutil.copyfile(PROBE, workdir / PROBE.name)
    for name in ("home", "tmp"):
        (workdir / name).mkdir()


def run_consumer(
    python: Path, workdir: Path, env: Mapping[str, str], *, extra: bool
) -> dict:
    """Run and validate the consumer matrix inside one environment.

    Args:
        python: Environment interpreter.
        workdir: Consumer working directory.
        env: Consumer environment.
        extra: Whether the environment installed the ``mcp`` extra.

    Returns:
        The validated consumer receipt.
    """
    command = [
        str(python),
        PROBE.name,
        "run",
        "tests.fixtures.providers.consumer_checks",
    ]
    command.append("mcp" if extra else "base")
    completed = run_process(command, dict(env), workdir, CHILD_TIMEOUT)
    receipt = parse_receipt(completed, "provider-consumer")
    validate_consumer(receipt, extra=extra)
    return receipt


def run_absent(python: Path, workdir: Path, env: Mapping[str, str]) -> dict:
    """Prove the base install imports the fakes but refuses the kit.

    Args:
        python: Environment interpreter.
        workdir: Consumer working directory.
        env: Consumer environment.

    Returns:
        The validated absence receipt.

    Raises:
        RuntimeError: The receipt differs from the expected refusal.
    """
    module = "tests.fixtures.providers.conformance_absent"
    command = [str(python), PROBE.name, "run", module]
    completed = run_process(command, dict(env), workdir, CHILD_TIMEOUT)
    receipt = parse_receipt(completed, "conformance-absent")
    if receipt != EXPECTED_ABSENT:
        raise RuntimeError(f"Base install conformance receipt differs: {receipt}")
    return receipt


def validate_kit_run(
    completed: subprocess.CompletedProcess[str],
    side: Mapping[str, Any],
    purelib: Path,
    checkout: Path,
) -> None:
    """Require every kit rule to pass against the installed kit, offline.

    Args:
        completed: The finished pytest child.
        side: The child's origin receipt.
        purelib: The environment's site-packages.
        checkout: Repository checkout.

    Raises:
        RuntimeError: A rule did not pass, or the kit loaded from elsewhere.
    """
    lines = completed.stdout.strip().splitlines()
    summary = lines[-1] if lines else ""
    if completed.returncode != 0 or not summary.startswith(f"{KIT_RULES} passed "):
        raise RuntimeError(f"Conformance kit run failed: {lines[-5:]}")
    origins = side.get("origins") or {}
    if KIT_MODULE not in origins:
        raise RuntimeError("The conformance kit module was not loaded")
    check_origins(origins, purelib, checkout)
    if side.get("network") != BLOCKED or side.get("preimport") != []:
        raise RuntimeError("The conformance run was not guarded before import")


def check_conformance_environment(
    wheel: Path, label: str, root: Path, version: str
) -> dict[str, Any]:
    """Install one wheel with the conformance extra and run the kit under pytest.

    Args:
        wheel: Wheel to install.
        label: Artifact label.
        root: Temporary root outside the checkout.
        version: Artifact version.

    Returns:
        A bounded receipt for this environment.

    Raises:
        RuntimeError: The identity, inventory or kit run fails.
    """
    env_dir = root / f"{label}-{CONFORMANCE_EXTRA}"
    python = create_venv(env_dir)
    install_wheel(python, wheel, (CONFORMANCE_EXTRA,))
    workdir = env_dir / "work"
    stage(workdir)
    env = consumer_env(workdir, python)
    probe = [str(python), PROBE.name, "identity", str(ROOT), "base"]
    identity = parse_receipt(
        run_process(probe, env, workdir, CHILD_TIMEOUT), "provider-identity"
    )
    if identity.get("version") != version:
        raise RuntimeError("Installed version differs from the artifact")
    purelib = Path(str(identity.get("purelib")))
    if not purelib.resolve().is_relative_to((env_dir / "venv").resolve()):
        raise RuntimeError("site-packages is outside the environment")
    check_origins(identity.get("origins") or {}, purelib, ROOT)
    graph = {
        normalize(name): value["requires"]
        for name, value in dict(identity["distributions"]).items()
    }
    check_conformance_inventory(graph, identity["environment"])
    side = workdir / "kit-origins.json"
    command = [str(python), PROBE.name, "run", "pytest", "-q", "-p"]
    command += ["no:cacheprovider", KIT_TESTS]
    kit_env = dict(env) | {ORIGINS_VARIABLE: str(side)}
    completed = run_process(command, kit_env, workdir, CHILD_TIMEOUT)
    receipt = json.loads(side.read_text()) if side.is_file() else {}
    validate_kit_run(completed, receipt, purelib, ROOT)
    return {
        "receipt": "provider-environment",
        "wheel": label,
        "kind": CONFORMANCE_EXTRA,
        "wheel_sha256": sha256(wheel),
        "version": version,
        "purelib": str(purelib),
        "kit_origin": receipt["origins"][KIT_MODULE],
        "kit_summary": completed.stdout.strip().splitlines()[-1],
    }


def check_environment(
    wheel: Path, label: str, root: Path, version: str, *, extra: bool
) -> dict[str, Any]:
    """Install one wheel into a fresh environment and prove it.

    The base environment also runs the conformance absence probe.

    Args:
        wheel: Wheel to install.
        label: Artifact label.
        root: Temporary root outside the checkout.
        version: Artifact version.
        extra: Whether to install the ``mcp`` extra.

    Returns:
        A bounded receipt for this environment.
    """
    kind = "mcp" if extra else "base"
    env_dir = root / f"{label}-{kind}"
    python = create_venv(env_dir)
    install_wheel(python, wheel, ("mcp",) if extra else ())
    workdir = env_dir / "work"
    stage(workdir)
    env = consumer_env(workdir, python)
    probe = [str(python), PROBE.name, "identity", str(ROOT), kind]
    identity = parse_receipt(
        run_process(probe, env, workdir, CHILD_TIMEOUT), "provider-identity"
    )
    validate_identity(identity, version, env_dir / "venv", ROOT, extra=extra)
    consumer = run_consumer(python, workdir, env, extra=extra)
    validate_children(consumer, Path(identity["purelib"]), ROOT, extra=extra)
    if not extra:
        run_absent(python, workdir, env)
    return environment_receipt(label, kind, sha256(wheel), identity, consumer)


def _artifacts(root: Path) -> tuple[Path, Path, Path, str]:
    """Build the source wheel and archive, then rebuild from the archive.

    Args:
        root: Temporary root outside the checkout.

    Returns:
        Source wheel, source archive, rebuilt wheel and version.

    Raises:
        RuntimeError: The build does not produce exactly one source archive.
    """
    dist = root / "dist"
    dist.mkdir()
    source = build_wheel(dist)
    archives = sorted(dist.glob("*.tar.gz"))
    if len(archives) != 1:
        raise RuntimeError("Expected exactly one source archive")
    rebuilt_dir = root / "sdist-wheel"
    rebuilt_dir.mkdir()
    rebuilt = rebuild_from_sdist(archives[0], rebuilt_dir, root)
    return source, archives[0], rebuilt, artifact_version(source, archives[0], rebuilt)


def main(argv: list[str]) -> int:
    """Build, install and prove all six environments.

    Args:
        argv: No arguments are accepted.

    Returns:
        Zero when every environment passes, otherwise one.
    """
    if argv:
        print("usage: smoke_provider_release.py")
        return 1
    root = Path(tempfile.mkdtemp(prefix="judgevet-provider-"))
    try:
        require_outside(root, ROOT)
        source, sdist, rebuilt, version = _artifacts(root)
        artifacts = {"source_wheel": sha256(source), "sdist": sha256(sdist)}
        artifacts["sdist_wheel"] = sha256(rebuilt)
        print(
            json.dumps(
                {"receipt": "provider-artifacts", "version": version} | artifacts
            )
        )
        for label, wheel in (("source", source), ("sdist", rebuilt)):
            for extra in (False, True):
                receipt = check_environment(wheel, label, root, version, extra=extra)
                print(json.dumps(receipt))
            receipt = check_conformance_environment(wheel, label, root, version)
            print(json.dumps(receipt))
    except (RuntimeError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        print(f"smoke_provider_release: FAIL — {error}")
        return 1
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("smoke_provider_release: PASS — six installed environments passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
