"""Verify the MCP hosted path picks the model each tool call requests."""

from __future__ import annotations

import pytest
from mcp.types import CallToolRequestParams

from judgevet.adapters.inbound import mcp_entrypoint as entry
from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.testing import FakeSystemOnePort

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(entry.stdio_server is None, reason="requires MCP extra"),
]

# The ask_* tools send raw question mappings, which the fake answers only
# when scripted. evaluate_policy sends a typed Noul, which it seeds.
SCRIPTED = {
    "noul_question": NoulAnswer(noul=0.5),
    "choice_question": ChoiceAnswer(
        choice="blue", confidence=1.0, probabilities={"blue": 1.0}
    ),
    "score_question": ScoreAnswer(
        score=2.0,
        confidence=0.8,
        legend={0: "Poor", 1: "Fair", 2: "Good", 3: "Excellent"},
        probabilities={0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25},
    ),
}


class ClosableFakePort(FakeSystemOnePort):
    """Add the no-op close the entry point calls on shutdown."""

    def close(self) -> None:
        """Release nothing; the fake holds no resource."""


TOOL_CALLS = [
    ("ask_noul", {"state": "The sky is blue.", "instruction": "Is the sky blue?"}),
    (
        "ask_choice",
        {
            "state": "The sky is blue.",
            "instruction": "Which colour?",
            "criteria": {"blue": "Blue", "red": "Red"},
        },
    ),
    ("ask_score", {"state": "The sky is blue.", "instruction": "How clear?"}),
    (
        "evaluate_policy",
        {
            "state": "The sky is blue.",
            "questions": {"clear": {"type": "noul", "instructions": "Is it clear?"}},
            "policy": {
                "rules": [{"question": "clear", "pass": {"noul": {"min": 0.0}}}]
            },
        },
    ),
]


@pytest.mark.parametrize(
    ("env_model", "model", "expected"),
    [
        ("jev-1.13.0", None, "jev-1.13.0"),
        (None, None, "jev-latest"),
        ("jev-1.13.0", "jev-9.9.9", "jev-9.9.9"),
    ],
    ids=["setting-fills-default", "unset-requests-latest", "explicit-model-wins"],
)
def test_every_tool_uses_the_selected_model(
    monkeypatch: pytest.MonkeyPatch,
    env_model: str | None,
    model: str | None,
    expected: str,
) -> None:
    """Require all four tools to call the port with the selected model."""
    monkeypatch.setenv("JEV_API__KEY", "judgevet-canary-216")
    if env_model is None:
        monkeypatch.delenv("JEV_API__DEFAULT_MODEL", raising=False)
    else:
        monkeypatch.setenv("JEV_API__DEFAULT_MODEL", env_model)
    port = ClosableFakePort(answers=SCRIPTED)

    def build(settings: object) -> ClosableFakePort:
        return port

    async def serve(acquired: ClosableFakePort, *, model: str = "jev-latest") -> None:
        server = create_mcp_server(acquired, model=model)
        async with server.lifespan(server):
            for name, arguments in TOOL_CALLS:
                result = await server._request_handlers["tools/call"].handler(
                    None, CallToolRequestParams(name=name, arguments=arguments)
                )
                assert result.is_error is False, result.content

    monkeypatch.setattr(entry, "build_adapter", build)
    monkeypatch.setattr(entry, "run_stdio", serve)

    exit_code = entry.main() if model is None else entry.main(model=model)
    assert exit_code == 0
    assert len(port.calls) == 4
    assert [call[2] for call in port.calls] == [expected] * 4
