"""Observe installed library, CLI and MCP provider behaviour for #205.

Usage: ``python -m tests.fixtures.providers.consumer_checks base|mcp`` from a
working directory outside the checkout. The module reports raw observations
in one JSON receipt line; the runner compares them with its own oracle.
Library checks run in-process. CLI and MCP checks run the application
wrappers as child processes through the network-guarding bootstrap and speak
real stdio, both as raw JSON-RPC lines and through the installed MCP SDK
client. Each child writes its loaded judgevet module files to a side receipt.
"""

import asyncio
import base64
import importlib.util
import json
import os
import socket
import sys
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Any, Protocol

import httpx

try:
    import mcp
except ModuleNotFoundError as missing:
    if missing.name != "mcp":
        raise
    mcp = None

from judgevet import HTTPSystemOneAdapter, RetryPolicy, SystemOneResponse
from judgevet.media import judge_with_images
from judgevet.media_audit import media_provenance
from judgevet.policy import evaluate_policy
from judgevet.policy_json import parse_policy
from judgevet.providers import ProviderError, provider_scope
from tests.fixtures.providers.provider_fixture import (
    BOOTSTRAP,
    EVENTS_VARIABLE,
    IMAGES,
    JPEG,
    ORIGINS_VARIABLE,
    PNG,
    POLICY,
    REQUESTED_MODEL,
    REVIEW,
    STATE,
    RecordingProvider,
    TextOnlyProvider,
    describe,
    drain,
    evidence,
    failing_setup,
    invalid_port,
    owned,
    to_findings,
    to_questions,
)

SYNTHETIC_KEY = "synthetic-offline-key"
AUDIT_KEY = b"fixture-audit-key"
_TIMEOUT = 60
_HOSTED = {
    "model": "jev-hosted-fixture",
    "usage": {"input_tokens": 3, "output_tokens": 2},
    "answers": {
        "support": {
            "type": "choice",
            "choice": "supported",
            "confidence": 0.7,
            "probabilities": {
                "supported": 0.7,
                "contradicted": 0.2,
                "insufficient_evidence": 0.1,
            },
        },
        "legible": {"type": "noul", "noul": 0.9},
        "quality": {
            "type": "score",
            "score": 1.0,
            "confidence": 0.5,
            "legend": {"0": "poor", "1": "fair", "2": "good"},
            "probabilities": {"0": 0.1, "1": 0.4, "2": 0.5},
        },
    },
}


def _events() -> list[list[Any]]:
    """Return fixture lifecycle events without call payloads.

    Returns:
        ``[event, provider]`` pairs recorded since the last drain.
    """
    return [[item["event"], item.get("provider")] for item in drain()]


def _envelope(response: SystemOneResponse) -> dict[str, Any]:
    """Summarize resolved model, usage and translated findings.

    Args:
        response: Typed response.

    Returns:
        Observed response metadata and application findings.
    """
    usage = [response.usage.input_tokens, response.usage.output_tokens]
    return {"model": response.model, "usage": usage, "findings": to_findings(response)}


def _policy(response: SystemOneResponse) -> list[Any]:
    """Evaluate the fixture policy against typed answers.

    Args:
        response: Typed response.

    Returns:
        Overall decision followed by ``[question, passed]`` per rule.
    """
    policy = parse_policy(json.dumps(POLICY), to_questions(REVIEW))
    report = evaluate_policy(policy, response.answers)
    return [report.passed, [[rule.question, rule.passed] for rule in report.rules]]


def library_text() -> dict[str, Any]:
    """Borrow a provider for a text call and leave it open.

    Returns:
        Observed call, response, policy and lifecycle.
    """
    drain()
    provider = RecordingProvider("borrowed-library")
    with provider_scope(port=provider) as port:
        response = port.system_one(STATE, to_questions(REVIEW), REQUESTED_MODEL)
    return _envelope(response) | {
        "policy": _policy(response),
        "calls": provider.calls,
        "closed": provider.closed,
        "events": _events(),
    }


def _media(bindings: Mapping[str, Sequence[str]], required: Sequence[str]) -> Any:
    """Judge fixture evidence with a borrowed media provider.

    Args:
        bindings: Question associations.
        required: Questions requiring evidence.

    Returns:
        Observed call, response and policy.
    """
    drain()
    provider = RecordingProvider("borrowed-library")
    used = {ref for refs in bindings.values() for ref in refs}
    images = [image for image in IMAGES if image[0] in used]
    response = judge_with_images(
        provider,
        STATE,
        to_questions(REVIEW),
        REQUESTED_MODEL,
        evidence=evidence(bindings, images, required),
    )
    return _envelope(response) | {
        "policy": _policy(response),
        "calls": provider.calls,
        "events": _events(),
    }


def library_media() -> dict[str, Any]:
    """Judge two ordered images with per-question bindings.

    Returns:
        Observed exact bytes, order, bindings, unknown usage and policy.
    """
    return _media({"support": ["page-2", "page-1"], "legible": ["page-1"]}, ["support"])


def library_insufficient() -> dict[str, Any]:
    """Return an ordinary insufficient-evidence outcome, not an error.

    Returns:
        Observed findings and failed policy for unbound support evidence.
    """
    return _media({"legible": ["page-1"]}, [])


def _failure(action: Callable[[], object]) -> str | None:
    """Run an action and name the declared provider failure it raised.

    Args:
        action: Callable expected to raise.

    Returns:
        Failure class name, or None when nothing raised.
    """
    try:
        action()
    except ProviderError as error:
        return type(error).__name__
    return None


def library_unsupported() -> dict[str, Any]:
    """Refuse media without support or with an undeclared type, without fallback.

    Returns:
        Failure classes and the calls each provider received.
    """
    drain()
    questions = to_questions(REVIEW)
    text_only = TextOnlyProvider("text-only-library")
    png_only = RecordingProvider("png-only-library", image_types=("image/png",))
    results = [
        _failure(
            partial(
                judge_with_images,
                port,
                STATE,
                questions,
                REQUESTED_MODEL,
                evidence=evidence(),
            )
        )
        for port in (text_only, png_only)
    ]
    return {
        "errors": results,
        "calls": [len(text_only.inner.calls), len(png_only.calls)],
        "events": _events(),
    }


def _owned_call(factory: Callable[[], Any]) -> dict[str, Any]:
    """Call through an owning factory and observe failure and lifecycle.

    Args:
        factory: Application provider factory.

    Returns:
        Failure class, resolved model and events.
    """
    drain()
    fallback = RecordingProvider("fallback-library")
    models: list[str] = []

    def call() -> None:
        with provider_scope(factory=factory) as port:
            response = port.system_one(STATE, to_questions(REVIEW), REQUESTED_MODEL)
            models.append(response.model)

    error = _failure(call)
    return {
        "error": error,
        "models": models,
        "fallback_calls": len(fallback.calls),
        "events": _events(),
    }


def library_owned() -> dict[str, Any]:
    """Acquire, use and close an owned provider exactly once.

    Returns:
        Observed model and lifecycle.
    """
    return _owned_call(partial(owned, "owned-library"))


def library_call_failure() -> dict[str, Any]:
    """Close an owned provider once when its call fails, with no fallback.

    Returns:
        Observed failure and lifecycle.
    """
    return _owned_call(partial(owned, "failing-library", fail=True))


def library_setup_failure() -> dict[str, Any]:
    """Propagate an acquisition failure after the application's rollback.

    Returns:
        Observed failure and lifecycle.
    """
    return _owned_call(partial(failing_setup, "setup-library"))


def library_invalid_port() -> dict[str, Any]:
    """Close an owned context once when it yields a non-port.

    Returns:
        Observed failure and lifecycle.
    """
    return _owned_call(partial(invalid_port, "invalid-library"))


def library_hosted() -> dict[str, Any]:
    """Exercise the default hosted adapter through an offline mock transport.

    Returns:
        Observed request line, body, credential match and parsed response.
    """
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_HOSTED)

    with HTTPSystemOneAdapter(
        api_key=SYNTHETIC_KEY,
        transport=httpx.MockTransport(handle),
        retry=RetryPolicy(max_attempts=1),
    ) as adapter:
        response = adapter.system_one(STATE, to_questions(REVIEW), REQUESTED_MODEL)
    request = seen[0]
    return _envelope(response) | {
        "requests": len(seen),
        "method": request.method,
        "url": str(request.url),
        "credential": request.headers.get("authorization") == f"Bearer {SYNTHETIC_KEY}",
        "body": json.loads(request.content),
    }


def library_provenance() -> dict[str, Any]:
    """Fingerprint evidence without retaining raw content.

    Returns:
        Observed identities, bindings, stability and sensitivity.
    """
    questions = to_questions(REVIEW)
    build = partial(
        media_provenance,
        questions=questions,
        fingerprint_key=AUDIT_KEY,
        prompt_revision="review-prompt-1",
        provider_identity="borrowed-library",
    )
    first, again = build(evidence()), build(evidence())
    altered = build(evidence(images=(IMAGES[0], ("page-2", JPEG + b"!", "image/jpeg"))))
    digests = [first.evidence_fingerprint, first.request_fingerprint]
    digests.extend(digest for _, digest in first.attachments)
    text = repr(first)
    return {
        "ids": [name for name, _ in first.attachments],
        "by_question": {key: list(value) for key, value in first.by_question.items()},
        "revisions": [
            first.prompt_revision,
            first.provider_identity,
            first.preprocessing_revision,
        ],
        "stable": first == again,
        "evidence_sensitive": altered.evidence_fingerprint
        != first.evidence_fingerprint,
        "request_unchanged": altered.request_fingerprint == first.request_fingerprint,
        "digests_distinct": len(set(digests)) == len(digests),
        "raw_absent": PNG.hex() not in text and "fixture-page" not in text,
    }


LIBRARY: dict[str, Callable[[], dict[str, Any]]] = {
    "library_text": library_text,
    "library_media": library_media,
    "library_insufficient": library_insufficient,
    "library_unsupported": library_unsupported,
    "library_owned": library_owned,
    "library_call_failure": library_call_failure,
    "library_setup_failure": library_setup_failure,
    "library_invalid_port": library_invalid_port,
    "library_hosted": library_hosted,
    "library_provenance": library_provenance,
}


def library_checks() -> dict[str, dict[str, Any]]:
    """Run every in-process library check.

    Returns:
        Observations keyed by check name.
    """
    return {name: check() for name, check in LIBRARY.items()}


def raw_questions() -> dict[str, dict[str, Any]]:
    """Serialize the translated questions for CLI and MCP arguments.

    Returns:
        Raw question definitions in application order.
    """
    result = {}
    for name, (kind, instructions, criteria) in describe(to_questions(REVIEW)).items():
        result[name] = {"type": kind, "instructions": instructions}
        if criteria is not None:
            result[name]["criteria"] = criteria
    return result


def _manifest(workdir: Path) -> dict[str, Path]:
    """Write CLI evidence, policy and images into the working directory.

    Args:
        workdir: Isolated consumer directory.

    Returns:
        Paths for the evidence manifest and the policy file.
    """
    inputs = workdir / "inputs"
    inputs.mkdir(exist_ok=True)
    entries = []
    for name, data, kind in IMAGES:
        path = inputs / f"{name}.bin"
        path.write_bytes(data)
        entries.append({"id": name, "path": path.name, "media_type": kind})
    manifest = {
        "images": entries,
        "by_question": {"support": ["page-2", "page-1"], "legible": ["page-1"]},
        "required": ["support"],
    }
    (inputs / "evidence.json").write_text(json.dumps(manifest))
    (inputs / "policy.json").write_text(json.dumps(POLICY))
    return {"evidence": inputs / "evidence.json", "policy": inputs / "policy.json"}


def summarize(data: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a rendered CLI or MCP envelope to its decision-bearing values.

    Args:
        data: Rendered response envelope.

    Returns:
        Model, usage, per-answer selections and the policy decision.
    """
    answers = [
        [name, item["type"], item[item["type"]], item.get("confidence")]
        for name, item in data["answers"].items()
    ]
    result = {"model": data["model"], "usage": data["usage"], "answers": answers}
    if "policy" in data:
        rules = [[rule["question"], rule["pass"]] for rule in data["policy"]["rules"]]
        result["policy"] = [data["policy"]["result"], rules]
    return result


def _read_events(path: Path) -> dict[str, Any]:
    """Split a child's events file into calls and lifecycle events.

    Args:
        path: Events file written by the child.

    Returns:
        Call payloads and ``[event, provider-or-closed]`` pairs.
    """
    lines = path.read_text().splitlines() if path.exists() else []
    items = [json.loads(line) for line in lines]
    calls = [
        {key: value for key, value in item.items() if key != "event"}
        for item in items
        if item["event"] == "call"
    ]
    events = [
        [item["event"], item.get("provider", item.get("closed"))] for item in items
    ]
    return {"calls": calls, "events": events}


CHILDREN: dict[str, Any] = {}
CLI_APP = "tests.fixtures.providers.cli_app"
MCP_APP = "tests.fixtures.providers.mcp_app"


def _child_files(workdir: Path, label: str) -> tuple[Path, Path]:
    """Create fresh events and origin receipt paths for one child.

    Args:
        workdir: Isolated working directory.
        label: Unique child label.

    Returns:
        Events file and origin receipt file.
    """
    paths = workdir / "events" / f"{label}.jsonl", workdir / "origins" / f"{label}.json"
    for path in paths:
        path.parent.mkdir(exist_ok=True)
        path.unlink(missing_ok=True)
    return paths


def _child_env(events: Path, origins: Path) -> dict[str, str]:
    """Extend the isolated consumer environment with child side channels.

    Args:
        events: Events file for this child.
        origins: Origin receipt file for this child.

    Returns:
        Child environment.
    """
    return os.environ | {EVENTS_VARIABLE: str(events), ORIGINS_VARIABLE: str(origins)}


def _collect(label: str, origins: Path) -> None:
    """Keep one child's origin receipt outside the semantic observations.

    Args:
        label: Child label.
        origins: Origin receipt written by the bootstrap.
    """
    CHILDREN[label] = json.loads(origins.read_text()) if origins.exists() else None


async def _spawn(
    module: str, arguments: Sequence[str], workdir: Path, label: str
) -> tuple[asyncio.subprocess.Process, Path, Path]:
    """Start one fixture wrapper through the network-guarding bootstrap.

    Args:
        module: Wrapper module name.
        arguments: Wrapper arguments.
        workdir: Isolated working directory.
        label: Unique child label.

    Returns:
        Child with piped standard streams, its events file and origin file.
    """
    events, origins = _child_files(workdir, label)
    child = await asyncio.create_subprocess_exec(
        sys.executable,
        BOOTSTRAP,
        "run",
        module,
        *arguments,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=workdir,
        env=_child_env(events, origins),
    )
    return child, events, origins


async def _cli(workdir: Path, label: str, arguments: Sequence[str]) -> dict[str, Any]:
    """Run the application CLI and observe status, output and events.

    Args:
        workdir: Isolated working directory.
        label: Unique events label.
        arguments: Mode and command arguments.

    Returns:
        Exit status, decoded output, diagnostic and events.
    """
    child, events, origins = await _spawn(CLI_APP, arguments, workdir, label)
    stdout, stderr = await asyncio.wait_for(child.communicate(), _TIMEOUT)
    _collect(label, origins)
    text = stdout.decode()
    return {
        "code": child.returncode,
        "output": summarize(json.loads(text)) if text.strip() else None,
        "error": stderr.decode().strip(),
    } | _read_events(events)


async def cli_checks(workdir: Path) -> dict[str, dict[str, Any]]:
    """Run the installed CLI through borrowed and owned application wrappers.

    Args:
        workdir: Isolated working directory.

    Returns:
        Observations keyed by check name.
    """
    paths = _manifest(workdir)
    common = ["--json", "--model", REQUESTED_MODEL]
    inputs = [json.dumps(STATE), json.dumps(raw_questions())]
    media = ["--evidence-file", str(paths["evidence"])]
    policy = ["--policy", str(paths["policy"])]
    plans = {
        "cli_text_borrowed": ["borrowed", *common, *inputs],
        "cli_media_owned": ["owned", *common, *media, *policy, *inputs],
        "cli_insufficient": ["owned", *common, *policy, *inputs],
        "cli_call_failure": ["failing", *common, *inputs],
        "cli_unsupported": ["text-only", *common, *media, *inputs],
    }
    return {name: await _cli(workdir, name, args) for name, args in plans.items()}


async def _rpc(
    child: asyncio.subprocess.Process, ident: int, method: str, params: Any
) -> dict[str, Any]:
    """Send one JSON-RPC request and read its matching response.

    Args:
        child: Running MCP server.
        ident: Request identifier.
        method: JSON-RPC method.
        params: Request parameters.

    Returns:
        The response result object.

    Raises:
        RuntimeError: The server closed its output or returned an error.
    """
    assert child.stdin is not None and child.stdout is not None
    frame = {"jsonrpc": "2.0", "id": ident, "method": method, "params": params}
    child.stdin.write((json.dumps(frame) + "\n").encode())
    await child.stdin.drain()
    while True:
        line = await asyncio.wait_for(child.stdout.readline(), _TIMEOUT)
        if not line:
            raise RuntimeError("MCP server closed its output")
        message = json.loads(line)
        if message.get("id") == ident:
            if "result" not in message:
                raise RuntimeError("MCP request failed")
            return message["result"]


def _tool(result: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize one tool result.

    Args:
        result: ``tools/call`` result.

    Returns:
        Error flag, text content and structured content.
    """
    text = [item.get("text") for item in result.get("content", [])]
    data = result.get("structuredContent")
    if data is None:
        return {"error": result.get("isError"), "text": text}
    return {
        "error": result.get("isError"),
        "text_matches": [json.loads(item) for item in text] == [data],
        "data": summarize(data),
    }


def _evidence_text() -> str:
    """Encode the fixture evidence as the MCP embedded JSON argument.

    Returns:
        Strict JSON text with base64 attachments.
    """
    images = [
        {"id": name, "data_base64": base64.b64encode(data).decode(), "media_type": kind}
        for name, data, kind in IMAGES
    ]
    bindings = {"support": ["page-2", "page-1"], "legible": ["page-1"]}
    return json.dumps(
        {"images": images, "by_question": bindings, "required": ["support"]}
    )


async def _session(workdir: Path, mode: str, label: str) -> dict[str, Any]:
    """Serve one MCP session over raw stdio lines and call the policy tool twice.

    Args:
        workdir: Isolated working directory.
        mode: Wrapper mode.
        label: Unique child label.

    Returns:
        Tool list, media then text results, exit status and events.
    """
    child, events, origins = await _spawn(MCP_APP, [mode], workdir, label)
    assert child.stdin is not None
    client = {"name": "provider-fixture", "version": "1"}
    init = {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": client}
    await _rpc(child, 1, "initialize", init)
    child.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    tools = await _rpc(child, 2, "tools/list", {})
    arguments = {"state": STATE, "questions": raw_questions(), "policy": POLICY}
    media = await _rpc(
        child,
        3,
        "tools/call",
        {
            "name": "evaluate_policy",
            "arguments": arguments | {"evidence": _evidence_text()},
        },
    )
    text = await _rpc(
        child, 4, "tools/call", {"name": "evaluate_policy", "arguments": arguments}
    )
    child.stdin.close()
    await asyncio.wait_for(child.communicate(), _TIMEOUT)
    _collect(label, origins)
    return {
        "tools": sorted(tool["name"] for tool in tools["tools"]),
        "media": _tool(media),
        "text": _tool(text),
        "code": child.returncode,
    } | _read_events(events)


class ToolResult(Protocol):
    """The SDK ``CallToolResult`` fields the consumer reads.

    Attributes:
        is_error: Whether the tool reported an error.
        content: Content blocks; text blocks carry ``type`` and ``text``.
        structured_content: Structured result, if any.
    """

    @property
    def is_error(self) -> bool | None:
        """Return whether the tool reported an error."""
        ...

    @property
    def content(self) -> Sequence[Any]:
        """Return the content blocks."""
        ...

    @property
    def structured_content(self) -> dict[str, Any] | None:
        """Return the structured result."""
        ...


def _sdk_tool(result: ToolResult) -> dict[str, Any]:
    """Summarize one SDK ``CallToolResult`` like the raw protocol summary.

    Args:
        result: Tool result object returned by ``ClientSession.call_tool``.

    Returns:
        Error flag, text or text agreement, and structured content summary.
    """
    text = [item.text for item in result.content if getattr(item, "type", "") == "text"]
    data = result.structured_content
    if data is None:
        return {"error": result.is_error, "text": text}
    return {
        "error": result.is_error,
        "text_matches": [json.loads(item) for item in text] == [data],
        "data": summarize(data),
    }


async def _sdk_session(workdir: Path, mode: str, label: str) -> dict[str, Any]:
    """Serve one MCP session through the installed SDK stdio client.

    Args:
        workdir: Isolated working directory.
        mode: Wrapper mode.
        label: Unique child label.

    Returns:
        Tool list, media then text results and events from SDK return objects.

    Raises:
        RuntimeError: The MCP SDK is not installed.
    """
    if mcp is None:
        raise RuntimeError("The MCP SDK client is not installed")
    events, origins = _child_files(workdir, label)
    server = mcp.StdioServerParameters(
        command=sys.executable,
        args=[BOOTSTRAP, "run", MCP_APP, mode],
        env=_child_env(events, origins),
        cwd=workdir,
    )
    arguments = {"state": STATE, "questions": raw_questions(), "policy": POLICY}
    with (workdir / "origins" / f"{label}.log").open("w") as log:
        async with (
            mcp.stdio_client(server, errlog=log) as (read, write),
            mcp.ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            media = await session.call_tool(
                "evaluate_policy", arguments | {"evidence": _evidence_text()}
            )
            text = await session.call_tool("evaluate_policy", arguments)
    _collect(label, origins)
    return {
        "tools": sorted(tool.name for tool in tools.tools),
        "media": _sdk_tool(media),
        "text": _sdk_tool(text),
    } | _read_events(events)


async def mcp_checks(workdir: Path) -> dict[str, dict[str, Any]]:
    """Serve owned and borrowed text-only providers through the installed SDK.

    Args:
        workdir: Isolated working directory.

    Returns:
        Observations keyed by check name.
    """
    return {
        "mcp_owned": await _session(workdir, "owned", "mcp_owned"),
        "mcp_text_only": await _session(workdir, "text-only", "mcp_text_only"),
        "mcp_sdk_owned": await _sdk_session(workdir, "owned", "mcp_sdk_owned"),
        "mcp_sdk_text_only": await _sdk_session(
            workdir, "text-only", "mcp_sdk_text_only"
        ),
    }


async def mcp_absent(workdir: Path) -> dict[str, dict[str, Any]]:
    """Confirm the base install refuses MCP before any provider acquisition.

    Args:
        workdir: Isolated working directory.

    Returns:
        Observation of the refused server start.
    """
    child, events, origins = await _spawn(MCP_APP, ["owned"], workdir, "mcp_absent")
    _, stderr = await asyncio.wait_for(child.communicate(b""), _TIMEOUT)
    _collect("mcp_absent", origins)
    return {
        "mcp_absent": {
            "code": child.returncode,
            "error": stderr.decode().strip(),
            "mcp_spec": importlib.util.find_spec("mcp") is not None,
        }
        | _read_events(events)
    }


def network_check() -> dict[str, Any]:
    """Confirm connection and name lookup attempts fail in this process.

    Both attempts stay on this machine, so no live call occurs without the guard.

    Returns:
        Failure class names for a loopback connect and a lookup.
    """
    names = []
    for attempt in (
        partial(socket.create_connection, ("127.0.0.1", 9), 1),
        partial(socket.getaddrinfo, "localhost", 9),
    ):
        try:
            attempt()
        except OSError as error:
            names.append(type(error).__name__)
        else:
            names.append(None)
    return {"network": {"errors": names}}


def main(argv: Sequence[str]) -> int:
    """Print one consumer receipt for ``base`` or ``mcp``.

    Args:
        argv: Environment kind.

    Returns:
        Zero after printing the receipt.
    """
    extra = argv[0] == "mcp"
    workdir = Path.cwd()
    checks: dict[str, Any] = library_checks() | network_check()
    checks |= asyncio.run(cli_checks(workdir))
    checks |= asyncio.run(mcp_checks(workdir) if extra else mcp_absent(workdir))
    origins = {
        name: str(module.__file__)
        for name, module in sorted(sys.modules.items())
        if name.split(".")[0] == "judgevet" and getattr(module, "__file__", None)
    }
    receipt = {"receipt": "provider-consumer", "extra": extra, "checks": checks}
    print(json.dumps(receipt | {"origins": origins, "children": CHILDREN}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
