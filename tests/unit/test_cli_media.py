"""Exercise explicit image manifests through public CLI applications offline."""

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from judgevet import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    SystemOneResponse,
    Usage,
)
from judgevet.adapters.inbound import cli
from judgevet.adapters.inbound.cli import create_cli_app
from judgevet.media import ImageEvidence, MediaCapabilities
from judgevet.providers import ProviderTransportError
from judgevet.testing import FakeSystemOnePort

QUESTIONS = {
    "claim": {"type": "noul", "instructions": {"check": ["image evidence"]}},
    "choice": {
        "type": "choice",
        "instructions": ["select an outcome"],
        "criteria": {"yes": "present", "insufficient_evidence": "unclear"},
    },
}


class MediaProvider:
    """Record exact image calls, text routes and lifetime events."""

    def __init__(self, *, outcome: str = "yes", fail: bool = False) -> None:
        """Select a semantic answer or a declared transport failure."""
        self.calls: list[
            tuple[
                object, Mapping[str, Question | Mapping[str, Any]], str, ImageEvidence
            ]
        ] = []
        self.text_calls = 0
        self.closed = 0
        self.outcome = outcome
        self.fail = fail

    def close(self) -> None:
        """Record an observable explicit resource release."""
        self.closed += 1

    def capabilities(self, model: str) -> MediaCapabilities:
        assert model == "selected-image-model"
        return MediaCapabilities({"image/png", "image/jpeg"})

    def response(self) -> SystemOneResponse:
        return SystemOneResponse(
            "resolved-image-model",
            Usage(0, None),
            {
                "claim": NoulAnswer(0.9),
                "choice": ChoiceAnswer(self.outcome, 0.8, {self.outcome: 1.0}),
            },
        )

    def system_one(self, state, questions, model) -> SystemOneResponse:
        self.text_calls += 1
        return self.response()

    def system_one_media(
        self, state, questions, model, *, evidence: ImageEvidence
    ) -> SystemOneResponse:
        assert self.closed == 0
        self.calls.append((state, questions, model, evidence))
        if self.fail:
            raise ProviderTransportError("fixture transport failed")
        return self.response()


def invocation(tmp_path: Path, *, policy: bool = False) -> tuple[list[str], Path]:
    """Build a relative-path manifest and an optional existing policy."""
    directory = tmp_path / "manifest-directory"
    directory.mkdir()
    (directory / "first.bin").write_bytes(b"\x00opaque-first\xff")
    (directory / "second.bin").write_bytes(b"\xffopaque-second\x00")
    manifest = directory / "evidence.json"
    manifest.write_text(
        json.dumps(
            {
                "images": [
                    {"id": "first", "path": "first.bin", "media_type": "image/png"},
                    {"id": "second", "path": "second.bin", "media_type": "image/jpeg"},
                ],
                "by_question": {"claim": ["second", "first"], "choice": ["first"]},
                "required": ["claim"],
            }
        )
    )
    args = [
        '{"record":["exact","state"]}',
        json.dumps(QUESTIONS),
        "--model",
        "selected-image-model",
        "--json",
        "--evidence-file",
        str(manifest),
    ]
    if policy:
        path = tmp_path / "policy.json"
        path.write_text(
            json.dumps({"rules": [{"question": "choice", "pass": {"choice": "yes"}}]})
        )
        args.extend(["--policy", str(path)])
    return args, manifest


@pytest.mark.parametrize("policy", [False, True])
def test_exact_images_through_borrowed_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: bool
) -> None:
    """Keep relative paths, exact bytes, both orders and original question data."""
    args, _ = invocation(tmp_path, policy=policy)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JEV_API__TIMEOUT_SECONDS", "invalid-hosted-setting")
    provider = MediaProvider()
    result = CliRunner().invoke(create_cli_app(port=provider), args)
    assert result.exit_code == 0, result.output
    assert provider.text_calls == 0
    assert provider.closed == 0
    assert len(provider.calls) == 1
    state, questions, model, evidence = provider.calls[0]
    assert state == {"record": ["exact", "state"]}
    assert model == "selected-image-model"
    assert [(item.id, item.data, item.media_type) for item in evidence.images] == [
        ("first", b"\x00opaque-first\xff", "image/png"),
        ("second", b"\xffopaque-second\x00", "image/jpeg"),
    ]
    assert dict(evidence.by_question) == {
        "claim": ("second", "first"),
        "choice": ("first",),
    }
    assert evidence.required == frozenset({"claim"})
    claim, choice = questions["claim"], questions["choice"]
    assert isinstance(claim, Noul)
    assert isinstance(choice, Choice)
    assert claim.instructions == {"check": ["image evidence"]}
    assert choice.instructions == ["select an outcome"]
    data = json.loads(result.stdout)
    assert data["model"] == "resolved-image-model"
    assert data["usage"] == {"input_tokens": 0, "output_tokens": None}
    assert data["answers"]["claim"]["type"] == "noul"
    assert data["answers"]["choice"]["type"] == "choice"
    if policy:
        assert data["policy"]["result"] == "pass"


@pytest.mark.parametrize(
    "outcome,fail,code",
    [("yes", False, 0), ("insufficient_evidence", False, 3), ("yes", True, 1)],
)
def test_owned_media_policy_cleanup(
    tmp_path: Path, outcome: str, fail: bool, code: int
) -> None:
    """Distinguish semantic failure from transport and release the owner once."""
    provider = MediaProvider(outcome=outcome, fail=fail)
    entered: list[bool] = []

    @contextmanager
    def factory() -> Iterator[MediaProvider]:
        entered.append(True)
        try:
            yield provider
        finally:
            provider.close()

    args, _ = invocation(tmp_path, policy=True)
    result = CliRunner().invoke(create_cli_app(provider_factory=factory), args)
    assert result.exit_code == code, result.output
    assert entered == [True]
    assert provider.closed == 1
    assert len(provider.calls) == 1
    if fail:
        assert result.stdout == ""
        assert json.loads(result.stderr)["error"] == "fixture transport failed"
    else:
        data = json.loads(result.stdout)
        assert data["policy"]["result"] == ("pass" if code == 0 else "fail")
        assert data["answers"]["choice"]["choice"] == outcome


@pytest.mark.parametrize(
    "defect",
    [
        "duplicate-key",
        "missing-required",
        "unknown-question",
        "unknown-image",
        "extra-field",
        "oversized-manifest",
        "oversized-image",
    ],
)
def test_bad_manifest_precedes_factory(tmp_path: Path, defect: str) -> None:
    """Reject bounded local input failures before acquiring the provider."""
    args, manifest = invocation(tmp_path)
    data = json.loads(manifest.read_text())
    if defect == "duplicate-key":
        manifest.write_text('{"images":[],"by_question":{},"by_question":{"claim":[]}}')
    elif defect == "oversized-manifest":
        manifest.write_bytes(b" " * (1024 * 1024 + 1))
    elif defect == "oversized-image":
        (manifest.parent / "first.bin").write_bytes(b"x" * (8 * 1024 * 1024 + 1))
    else:
        if defect == "missing-required":
            data = {"images": [], "by_question": {}, "required": ["claim"]}
        elif defect == "unknown-question":
            data["by_question"]["absent"] = ["first"]
        elif defect == "unknown-image":
            data["by_question"]["claim"] = ["absent"]
        else:
            data["images"][0]["unrecognized"] = "must-not-drop"
        manifest.write_text(json.dumps(data))

    @contextmanager
    def forbidden() -> Iterator[MediaProvider]:
        pytest.fail("invalid local manifest acquired provider")
        yield MediaProvider()

    result = CliRunner().invoke(create_cli_app(provider_factory=forbidden), args)
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]
    assert str(manifest) not in result.stderr


def test_hosted_route_rejects_nonempty_media_without_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep unverified HTTP media unsupported before credentials or transport."""

    def forbidden(**kwargs: object) -> None:
        pytest.fail("hosted media constructed an HTTP adapter")

    monkeypatch.setattr(cli, "HTTPSystemOneAdapter", forbidden)
    args, _ = invocation(tmp_path)
    result = CliRunner().invoke(create_cli_app(), args)
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert (
        "media" in json.loads(result.stderr)["error"].lower()
        or "image" in json.loads(result.stderr)["error"].lower()
    )


def test_empty_manifest_keeps_text_dispatch(tmp_path: Path) -> None:
    """Avoid media capability lookup for valid optional empty evidence."""
    args, manifest = invocation(tmp_path)
    manifest.write_text('{"images":[],"by_question":{}}')
    provider = MediaProvider()
    result = CliRunner().invoke(create_cli_app(port=provider), args)
    assert result.exit_code == 0, result.output
    assert provider.text_calls == 1
    assert provider.calls == []


def test_repeated_evidence_flag_is_an_input_error(tmp_path: Path) -> None:
    """Reject ambiguous manifest selection without dispatch."""
    args, manifest = invocation(tmp_path)
    provider = MediaProvider()
    result = CliRunner().invoke(
        create_cli_app(port=provider), [*args, "--evidence-file", str(manifest)]
    )
    assert result.exit_code == 1, result.output
    assert provider.calls == []
    assert provider.text_calls == 0


@pytest.mark.parametrize("policy", [False, True])
def test_empty_manifest_keeps_hosted_composition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: bool
) -> None:
    """Reuse the existing hosted composition route for valid empty evidence."""
    args, manifest = invocation(tmp_path, policy=policy)
    manifest.write_text('{"images":[],"by_question":{}}')
    calls: list[tuple[object, ...]] = []

    def hosted_main(state, questions, model, api_key, json_output) -> int:
        calls.append((state, questions, model, api_key, json_output))
        return 0

    def hosted_policy(
        state, questions, model, api_key, as_json, policy_file, callbacks
    ) -> int:
        calls.append((state, questions, model, api_key, as_json, policy_file))
        return 0

    monkeypatch.setattr(cli, "main", hosted_main)
    monkeypatch.setattr(cli, "run_policy", hosted_policy)
    result = CliRunner().invoke(create_cli_app(), args)
    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0][:5] == (
        '{"record":["exact","state"]}',
        json.dumps(QUESTIONS),
        "selected-image-model",
        None,
        True,
    )


def test_successful_insufficient_answer_without_policy(tmp_path: Path) -> None:
    """Keep explicit insufficient evidence an ordinary successful judgment."""
    args, _ = invocation(tmp_path)
    provider = MediaProvider(outcome="insufficient_evidence")
    result = CliRunner().invoke(create_cli_app(port=provider), args)
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["answers"]["choice"]["choice"] == "insufficient_evidence"
    assert "policy" not in data


def test_media_option_does_not_leak_to_next_invocation(tmp_path: Path) -> None:
    """Keep file-option state local when reusing the same application."""
    args, _ = invocation(tmp_path)
    provider = MediaProvider()
    app = create_cli_app(port=provider)
    first = CliRunner().invoke(app, args)
    second = CliRunner().invoke(app, args[:-2])
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert len(provider.calls) == 1
    assert provider.text_calls == 1
    assert provider.closed == 0


@pytest.mark.parametrize(
    "payload",
    [
        b'{"images":[],"by_question":{},"extra":1}',
        b'{"images":[],"by_question":{},"required":["claim","claim"]}',
        b'{"images":[],"by_question":{"claim":NaN}}',
        b'{"images":[],"by_question":{"claim":[],"claim":[]}}',
        b'{"images":[],"by_question":{},"required":"claim"}',
        b'{"images":[],"by_question":[]}',
        b'{"images":[],"by_question":{"claim":"first"}}',
        b'{"images":[],"by_question":{},"required":["unknown"]}',
        b"\xff",
        b"[]",
    ],
)
def test_strict_manifest_shapes_before_acquisition(
    tmp_path: Path, payload: bytes
) -> None:
    """Reject ambiguous JSON and malformed collections without leaking payloads."""
    args, manifest = invocation(tmp_path)
    manifest.write_bytes(payload)

    @contextmanager
    def forbidden() -> Iterator[MediaProvider]:
        pytest.fail("malformed manifest acquired provider")
        yield MediaProvider()

    result = CliRunner().invoke(create_cli_app(provider_factory=forbidden), args)
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert "--evidence-file" in json.loads(result.stderr)["error"]
    assert str(manifest) not in result.stderr


@pytest.mark.parametrize(
    "defect",
    [
        "duplicate",
        "unreferenced",
        "repeated-reference",
        "url",
        "empty",
        "missing",
        "count",
        "total",
    ],
)
def test_image_bounds_before_acquisition(tmp_path: Path, defect: str) -> None:
    """Enforce local declaration, count and byte limits before opening a provider."""
    args, manifest = invocation(tmp_path)
    data = json.loads(manifest.read_text())
    if defect == "duplicate":
        data["images"].append(data["images"][0])
    elif defect == "unreferenced":
        data["by_question"]["claim"] = ["first"]
    elif defect == "repeated-reference":
        data["by_question"]["claim"] = ["first", "first", "second"]
    elif defect == "url":
        data["images"][0]["path"] = "https://invalid.example/private-image"
    elif defect == "empty":
        (manifest.parent / "first.bin").write_bytes(b"")
    elif defect == "missing":
        data["images"][0]["path"] = "private-missing-image"
    else:
        count = 17 if defect == "count" else 5
        data["images"] = [
            {"id": str(i), "path": "first.bin", "media_type": "image/png"}
            for i in range(count)
        ]
        data["by_question"] = {"claim": [str(i) for i in range(count)]}
        if defect == "total":
            (manifest.parent / "first.bin").write_bytes(b"x" * (8 * 1024 * 1024))
    manifest.write_text(json.dumps(data))

    @contextmanager
    def forbidden() -> Iterator[MediaProvider]:
        pytest.fail("invalid images acquired provider")
        yield MediaProvider()

    result = CliRunner().invoke(create_cli_app(provider_factory=forbidden), args)
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert "--evidence-file" in json.loads(result.stderr)["error"]
    assert str(manifest) not in result.stderr


def test_selected_text_only_provider_rejects_images(tmp_path: Path) -> None:
    """Never convert nonempty image input into a successful text judgment."""
    args, _ = invocation(tmp_path)
    result = CliRunner().invoke(create_cli_app(port=FakeSystemOnePort()), args)
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert "media" in json.loads(result.stderr)["error"]


@pytest.mark.parametrize("option", ["--evidence-file", "--policy"])
@pytest.mark.parametrize("selected", [False, True])
def test_explicit_empty_path_is_not_omitted(option: str, selected: bool) -> None:
    """Treat an explicit empty path as an input error before any judgment."""
    provider = MediaProvider()
    application = create_cli_app(port=provider) if selected else cli.app
    result = CliRunner().invoke(
        application, ["state", json.dumps(QUESTIONS), option, "", "--json"]
    )
    assert result.exit_code == 1, result.output
    assert result.stdout == ""
    assert option in json.loads(result.stderr)["error"]
    assert provider.text_calls == 0
    assert provider.calls == []


@pytest.mark.parametrize("hosted", [False, True])
@pytest.mark.parametrize("policy", [False, True])
def test_missing_required_evidence_has_a_distinct_diagnostic(
    tmp_path: Path, hosted: bool, policy: bool
) -> None:
    """Keep missing evidence distinct from malformed input before acquisition."""
    args, manifest = invocation(tmp_path, policy=policy)

    @contextmanager
    def forbidden() -> Iterator[MediaProvider]:
        pytest.fail("invalid local evidence acquired a provider")
        yield MediaProvider()

    app = create_cli_app() if hosted else create_cli_app(provider_factory=forbidden)
    manifest.write_text('{"images":[],"by_question":{},"required":["claim"]}')
    missing = CliRunner().invoke(app, args)
    manifest.write_text('{"images":[],"by_question":42}')
    malformed = CliRunner().invoke(app, args)
    assert missing.exit_code == 1, missing.output
    assert malformed.exit_code == 1, malformed.output
    assert missing.stdout == malformed.stdout == ""
    missing_error = json.loads(missing.stderr)["error"]
    malformed_error = json.loads(malformed.stderr)["error"]
    assert missing_error != malformed_error
    assert "required" in missing_error.lower()
    assert str(manifest) not in missing.stderr
    assert "claim" not in missing.stderr
