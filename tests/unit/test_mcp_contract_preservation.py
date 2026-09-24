"""Freeze the existing public MCP output and invalid-answer contracts."""

import json
from pathlib import Path

import anyio
import pytest

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.domain.answers import NoulAnswer, ScoreAnswer
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from tests.unit.test_mcp_noul import FakeSystemOnePort, MockParams

FIXTURE = Path(__file__).parents[1] / "fixtures" / "mcp_contract.json"


def test_existing_discovery_and_results() -> None:
    """Compare executable discovery and all tool outputs with the original wire contract."""
    expected = json.loads(FIXTURE.read_text())
    server = create_mcp_server(FakeSystemOnePort())

    async def exercise() -> None:
        tools = await server._request_handlers["tools/list"].handler(None, None)
        assert tools.model_dump(mode="json", by_alias=True) == expected["tools"]
        for kind in ("noul", "choice", "score"):
            result = await server._request_handlers["tools/call"].handler(
                None,
                MockParams(
                    name=f"ask_{kind}",
                    arguments={"state": "test", "instruction": "test"},
                ),
            )
            assert (
                result.model_dump(mode="json", by_alias=True)
                == expected["results"][kind]
            )

    anyio.run(exercise)


@pytest.mark.parametrize("kind", ["noul", "choice", "score"])
@pytest.mark.parametrize("missing", [True, False])
def test_invalid_answer_contract(kind: str, missing: bool) -> None:
    """Require missing and mismatched answers to raise the existing diagnostics."""
    wrong = ScoreAnswer(score=0, confidence=1, legend={0: "x"}, probabilities={0: 1})
    response = SystemOneResponse(
        model="test",
        usage=Usage(input_tokens=0, output_tokens=0),
        answers={}
        if missing
        else {f"{kind}_question": wrong if kind == "noul" else NoulAnswer(noul=0)},
    )

    class InvalidPort(FakeSystemOnePort):
        def system_one(self, state, questions, model) -> SystemOneResponse:
            return response

    server = create_mcp_server(InvalidPort())

    async def call() -> None:
        await server._request_handlers["tools/call"].handler(
            None,
            MockParams(
                name=f"ask_{kind}", arguments={"state": "x", "instruction": "x"}
            ),
        )

    error = ValueError if missing else TypeError
    message = (
        f"No answer returned for {kind}_question"
        if missing
        else f"Expected {kind.title()}Answer, got"
    )
    with pytest.raises(error, match=message):
        anyio.run(call)
