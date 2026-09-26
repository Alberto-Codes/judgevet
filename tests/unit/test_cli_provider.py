"""Exercise application provider selection through actual CLI commands."""

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
    JudgmentRecord,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    SpendCap,
    SystemOneResponse,
    Usage,
)
from judgevet.adapters.inbound import cli, cli_policy_run
from judgevet.adapters.inbound.cli import create_cli_app
from judgevet.providers import ProviderTransportError, ProviderUnavailableError
from judgevet.testing import FakeSystemOnePort

QUESTIONS = {
    "claim": {"type": "noul", "instructions": {"rule": "check claim"}},
    "label": {
        "type": "choice",
        "instructions": "choose label",
        "criteria": {"yes": "supported", "no": "unsupported"},
    },
    "rating": {
        "type": "score",
        "instructions": ["rate evidence"],
        "criteria": ["weak", "strong"],
    },
}


class RecordingProvider:
    """Return all answer variants and record their public call inputs."""

    def __init__(self, *, fail: bool = False, noul: float = 0.9) -> None:
        """Initialize the synthetic call and lifetime recorder."""
        self.fail = fail
        self.noul = noul
        self.closed = 0
        self.calls: list[
            tuple[object, Mapping[str, Question | Mapping[str, Any]], str]
        ] = []

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Record exact inputs and return typed synthetic judgments."""
        assert self.closed == 0
        self.calls.append((state, questions, model))
        if self.fail:
            raise ProviderTransportError("synthetic transport failure")
        return SystemOneResponse(
            model="fixture-resolved-v1",
            usage=Usage(input_tokens=17),
            answers={
                "claim": NoulAnswer(self.noul),
                "label": ChoiceAnswer("yes", 0.8, {"yes": 0.8, "no": 0.2}),
                "rating": ScoreAnswer(
                    0.8, 0.8, {0: "weak", 1: "strong"}, {0: 0.2, 1: 0.8}
                ),
            },
        )

    def close(self) -> None:
        """Record owned cleanup."""
        self.closed += 1


def arguments(tmp_path: Path, policy: bool) -> list[str]:
    """Build an existing text policy invocation."""
    args = [
        '{"record":["exact","state"]}',
        json.dumps(QUESTIONS),
        "--model",
        "fixture-requested",
        "--json",
    ]
    if policy:
        path = tmp_path / "policy.json"
        path.write_text(
            json.dumps(
                {
                    "rules": [
                        {"question": "claim", "pass": {"noul": {"min": 0.8}}},
                        {"question": "label", "pass": {"choice": "yes"}},
                        {"question": "rating", "pass": {"score": {"min": 0.5}}},
                    ]
                }
            )
        )
        args.extend(["--policy", str(path)])
    return args


@pytest.mark.parametrize("policy", [False, True])
def test_borrowed_provider_preserves_full_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: bool,
) -> None:
    """Explicit selection bypasses hosted construction and preserves the contract."""

    def forbidden(**kwargs: object) -> None:
        pytest.fail("explicit provider reached hosted construction")

    monkeypatch.setattr(cli, "HTTPSystemOneAdapter", forbidden)
    monkeypatch.setattr(cli_policy_run, "HTTPSystemOneAdapter", forbidden)
    monkeypatch.setenv("JEV_API__TIMEOUT_SECONDS", "invalid-hosted-config")
    provider = RecordingProvider()
    result = CliRunner().invoke(
        create_cli_app(port=provider), arguments(tmp_path, policy)
    )
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert len(provider.calls) == 1
    state, questions, model = provider.calls[0]
    assert state == {"record": ["exact", "state"]}
    assert model == "fixture-requested"
    assert list(questions) == ["claim", "label", "rating"]
    assert isinstance(questions["claim"], Noul)
    assert isinstance(questions["label"], Choice)
    assert isinstance(questions["rating"], Score)
    assert questions["claim"].instructions == {"rule": "check claim"}
    assert questions["label"].instructions == "choose label"
    assert questions["rating"].instructions == ["rate evidence"]
    data = json.loads(result.stdout)
    assert data["model"] == "fixture-resolved-v1"
    assert data["usage"] == {"input_tokens": 17, "output_tokens": None}
    assert [answer["type"] for answer in data["answers"].values()] == [
        "noul",
        "choice",
        "score",
    ]
    if policy:
        assert data["policy"]["result"] == "pass"
    assert provider.closed == 0


@pytest.mark.parametrize(
    "noul,fail,status", [(0.9, False, 0), (0.1, False, 3), (0.9, True, 1)]
)
def test_owned_policy_outcomes_close_once(
    tmp_path: Path,
    noul: float,
    fail: bool,
    status: int,
) -> None:
    """Met, unmet and failed policy commands all release the selected owner."""
    provider = RecordingProvider(noul=noul, fail=fail)

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        try:
            yield provider
        finally:
            provider.close()

    result = CliRunner().invoke(
        create_cli_app(provider_factory=factory), arguments(tmp_path, True)
    )
    assert result.exit_code == status, result.output
    assert len(provider.calls) == 1
    assert provider.closed == 1
    if fail:
        assert result.stdout == ""
        assert json.loads(result.stderr)["error"]
    else:
        assert json.loads(result.stdout)["policy"]["result"] == (
            "pass" if status == 0 else "fail"
        )


def test_unavailable_factory_never_falls_back(tmp_path: Path) -> None:
    """An unavailable explicit selection is a handled command failure."""

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        raise ProviderUnavailableError("install application provider support")
        yield RecordingProvider()

    result = CliRunner().invoke(
        create_cli_app(provider_factory=factory), arguments(tmp_path, True)
    )
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "application provider" in json.loads(result.stderr)["error"]


def test_apps_keep_independent_selections(tmp_path: Path) -> None:
    """Building a second app cannot replace the first app's selected provider."""
    first, second = RecordingProvider(), RecordingProvider()
    app_one, app_two = create_cli_app(port=first), create_cli_app(port=second)
    for application in [app_one, app_two, app_one]:
        assert (
            CliRunner().invoke(application, arguments(tmp_path, False)).exit_code == 0
        )
    assert (len(first.calls), len(second.calls)) == (2, 1)
    assert (first.closed, second.closed) == (0, 0)


class Records:
    """Retain opt-in audit records from the selected provider."""

    def __init__(self) -> None:
        """Start with an empty caller-owned record collection."""
        self.items: list[JudgmentRecord] = []

    def record(self, record: JudgmentRecord) -> None:
        """Accept one terminal logical-call record."""
        self.items.append(record)


def test_selected_provider_keeps_its_audit_and_spend_contract(tmp_path: Path) -> None:
    """Command wiring preserves provider-owned audit and attempt accounting."""
    sink = Records()
    cap = SpendCap(max_attempts=1)
    answers = RecordingProvider().system_one("fixture", {}, "fixture").answers
    provider = FakeSystemOnePort(
        answers=answers,
        usage=Usage(input_tokens=5),
        spend_cap=cap,
        audit=sink,
    )
    application = create_cli_app(port=provider)
    runner = CliRunner()
    success = runner.invoke(application, arguments(tmp_path, True))
    refusal = runner.invoke(application, arguments(tmp_path, True))
    assert success.exit_code == 0, success.output
    assert refusal.exit_code == 1
    assert json.loads(refusal.stderr)["error"]
    assert (cap.attempts, cap.input_tokens) == (1, 5)
    assert [record.outcome for record in sink.items] == ["success", "error"]
    assert sink.items[0].usage == Usage(input_tokens=5)
    assert sink.items[1].error_type == "JevBudgetExceededError"
    assert list(sink.items[0].questions) == ["claim", "label", "rating"]


@pytest.mark.parametrize("policy", [False, True])
def test_invalid_inputs_precede_factory_acquisition(
    tmp_path: Path, policy: bool
) -> None:
    """Malformed questions never acquire an application resource."""
    acquired = []

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        acquired.append(True)
        yield RecordingProvider()

    args = arguments(tmp_path, policy)
    args[1] = '{"q":{"type":"invalid"}}'
    result = CliRunner().invoke(create_cli_app(provider_factory=factory), args)
    assert result.exit_code == 1
    assert acquired == []
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]


def test_conflicting_selections_rejected_without_acquisition() -> None:
    """An ambiguous application fails before touching its resources."""
    acquired = []

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        acquired.append(True)
        yield RecordingProvider()

    with pytest.raises(ValueError, match="at most one"):
        create_cli_app(port=RecordingProvider(), provider_factory=factory)
    assert acquired == []


def test_default_app_factory_keeps_hosted_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No explicit selection preserves the hosted composition root."""
    calls = []

    def hosted(**kwargs: object) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(cli, "main", hosted)
    result = CliRunner().invoke(create_cli_app(), arguments(tmp_path, False))
    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0]["model"] == "fixture-requested"
