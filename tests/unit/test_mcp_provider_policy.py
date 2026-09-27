"""Exercise keyed policies through the SDK's public server construction."""

import asyncio
import copy
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from mcp.types import CallToolRequestParams

from judgevet import Choice, Noul, Score, SpendCap, Usage
from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
from judgevet.testing import FakeSystemOnePort
from tests.unit.test_cli_provider import QUESTIONS, RecordingProvider, Records
from tests.unit.test_mcp_subprocess import environment, exchange, stop

POLICY = {
    "rules": [
        {"question": "claim", "pass": {"noul": {"min": 0.8}}},
        {"question": "label", "pass": {"choice": "yes"}},
        {"question": "rating", "pass": {"score": {"min": 0.5}}},
    ]
}
STATE = {"record": ["exact", "state"]}


def arguments() -> dict[str, object]:
    """Build the existing policy grammar with arbitrary keyed questions."""
    return {"state": STATE, "questions": copy.deepcopy(QUESTIONS), "policy": POLICY}


@pytest.mark.parametrize("noul,verdict", [(0.9, "pass"), (0.1, "fail")])
def test_policy_tool_preserves_full_request(noul: float, verdict: str) -> None:
    """Return all typed answers and distinguish unmet policy from tool failure."""
    provider = RecordingProvider(noul=noul)
    server = create_mcp_server(provider, model="fixture-requested")

    async def exercise() -> None:
        async with server.lifespan(server):
            discovery = await server._request_handlers["tools/list"].handler(None, None)
            names = [tool.name for tool in discovery.tools]
            assert names == ["ask_noul", "ask_choice", "ask_score", "evaluate_policy"]
            result = await server._request_handlers["tools/call"].handler(
                None,
                CallToolRequestParams(name="evaluate_policy", arguments=arguments()),
            )
            assert not result.is_error
            data = result.structured_content
            assert data["model"] == "fixture-resolved-v1"
            assert data["usage"] == {"input_tokens": 17, "output_tokens": None}
            assert list(data["answers"]) == ["claim", "label", "rating"]
            assert [a["type"] for a in data["answers"].values()] == [
                "noul",
                "choice",
                "score",
            ]
            assert data["policy"]["result"] == verdict
            assert [r["question"] for r in data["policy"]["rules"]] == [
                "claim",
                "label",
                "rating",
            ]
            assert json.loads(result.content[0].text) == data

    asyncio.run(exercise())
    assert len(provider.calls) == 1
    state, questions, model = provider.calls[0]
    assert state == STATE
    assert model == "fixture-requested"
    assert isinstance(questions["claim"], Noul)
    assert isinstance(questions["label"], Choice)
    assert isinstance(questions["rating"], Score)
    assert questions["claim"].instructions == {"rule": "check claim"}
    assert questions["label"].instructions == "choose label"
    assert questions["rating"].instructions == ["rate evidence"]
    assert provider.closed == 0


@pytest.mark.parametrize("defect", ["questions", "policy", "model"])
def test_invalid_request_never_dispatches(defect: str) -> None:
    """Reject invalid definitions and attempts to select a model through arguments."""
    provider = RecordingProvider()
    server = create_mcp_server(provider, model="fixture-requested")
    payload = arguments()
    if defect == "questions":
        payload["questions"] = {"claim": {"type": "unsupported"}}
    elif defect == "policy":
        payload["policy"] = {
            "rules": [{"question": "absent", "pass": {"noul": {"min": 0.8}}}]
        }
    else:
        payload["model"] = "untrusted-model"

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None, CallToolRequestParams(name="evaluate_policy", arguments=payload)
            )
            assert result.is_error
            assert "answers" not in (result.structured_content or {})

    asyncio.run(exercise())
    assert provider.calls == []


def test_provider_failure_is_not_policy_unmet() -> None:
    """Return a declared infrastructure failure without manufacturing policy answers."""
    provider = RecordingProvider(fail=True)
    server = create_mcp_server(provider)

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None,
                CallToolRequestParams(name="evaluate_policy", arguments=arguments()),
            )
            assert result.is_error
            assert "synthetic transport failure" in result.content[0].text
            assert "policy" not in (result.structured_content or {})

    asyncio.run(exercise())
    assert len(provider.calls) == 1
    assert provider.closed == 0


def test_policy_tool_preserves_opt_in_audit_and_spend() -> None:
    """Keep provider-owned logical records and physical-attempt accounting."""
    sink = Records()
    cap = SpendCap(max_attempts=1)
    answers = RecordingProvider().system_one("fixture", {}, "fixture").answers
    provider = FakeSystemOnePort(
        answers=answers, usage=Usage(5), spend_cap=cap, audit=sink
    )
    server = create_mcp_server(provider, model="fixture-requested")

    async def exercise() -> None:
        async with server.lifespan(server):
            handler = server._request_handlers["tools/call"].handler
            params = CallToolRequestParams(
                name="evaluate_policy", arguments=arguments()
            )
            success = await handler(None, params)
            refusal = await handler(None, params)
            assert not success.is_error
            assert success.structured_content["policy"]["result"] == "pass"
            assert refusal.is_error

    asyncio.run(exercise())
    assert (cap.attempts, cap.input_tokens) == (1, 5)
    assert [record.outcome for record in sink.items] == ["success", "error"]
    assert sink.items[0].usage == Usage(5)
    assert sink.items[1].error_type == "JevBudgetExceededError"
    assert list(sink.items[0].questions) == ["claim", "label", "rating"]


@pytest.mark.parametrize("fail", [False, True])
def test_owned_policy_cleanup(fail: bool) -> None:
    """Close an owned provider once after successful or failed policy dispatch."""
    provider = RecordingProvider(fail=fail)

    @contextmanager
    def factory() -> Iterator[RecordingProvider]:
        try:
            yield provider
        finally:
            provider.close()

    async def exercise() -> None:
        dispatch = ProviderDispatch(factory=factory)
        async with dispatch.session():
            assert dispatch.port is provider
            server = create_mcp_server(provider, model="fixture-requested")
            async with server.lifespan(server):
                result = await server._request_handlers["tools/call"].handler(
                    None,
                    CallToolRequestParams(
                        name="evaluate_policy", arguments=arguments()
                    ),
                )
                assert result.is_error is fail
            assert provider.closed == 0
        assert provider.closed == 1

    asyncio.run(exercise())
    assert len(provider.calls) == 1


def test_policy_over_actual_stdio() -> None:
    """Exercise an application-owned provider through real offline protocol frames."""
    program = """
from contextlib import contextmanager
from judgevet.adapters.inbound.mcp_entrypoint import main
from tests.unit.test_cli_provider import RecordingProvider
provider = RecordingProvider()
@contextmanager
def factory():
    try:
        yield provider
    finally:
        provider.close()
result = main(provider_factory=factory, model="fixture-requested")
assert provider.closed == 1
assert len(provider.calls) == 1
assert provider.calls[0][2] == "fixture-requested"
raise SystemExit(result)
"""

    async def exercise() -> None:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            program,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=environment(),
        )
        try:
            await exchange(
                process,
                1,
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "offline-policy-test", "version": "1"},
                },
            )
            assert process.stdin is not None
            process.stdin.write(
                b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
            )
            await process.stdin.drain()
            result = await exchange(
                process,
                2,
                "tools/call",
                {
                    "name": "evaluate_policy",
                    "arguments": arguments(),
                },
            )
            assert not result["isError"]
            assert result["structuredContent"]["policy"]["result"] == "pass"
            assert result["structuredContent"]["model"] == "fixture-resolved-v1"
            assert (
                json.loads(result["content"][0]["text"]) == result["structuredContent"]
            )
            process.stdin.close()
            await process.stdin.wait_closed()
            await process.wait()
            assert process.stderr is not None
            diagnostic = await process.stderr.read()
            assert process.returncode == 0, diagnostic.decode()
        finally:
            await stop(process)

    asyncio.run(asyncio.wait_for(exercise(), 15))


def test_invalid_policy_answer_is_tool_error() -> None:
    """Reject a mismatched answer variant instead of reporting an unmet policy."""
    answers = dict(RecordingProvider().system_one("fixture", {}, "fixture").answers)
    answers["claim"] = answers["label"]
    server = create_mcp_server(FakeSystemOnePort(answers=answers))

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None,
                CallToolRequestParams(name="evaluate_policy", arguments=arguments()),
            )
            assert result.is_error
            assert "answer type mismatch" in result.content[0].text
            assert not result.structured_content

    asyncio.run(exercise())


@pytest.mark.parametrize("question", ["claim", "label", "rating"])
def test_unsupported_question_field_never_dispatches(question: str) -> None:
    """Reject unsupported fields instead of silently discarding caller input."""
    provider = RecordingProvider()
    server = create_mcp_server(provider, model="fixture-requested")
    payload = arguments()
    definitions = payload["questions"]
    assert isinstance(definitions, dict)
    definitions[question]["extra"] = "must-not-drop"

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None,
                CallToolRequestParams(name="evaluate_policy", arguments=payload),
            )
            assert result.is_error, "unsupported question field was dispatched"
            assert "answers" not in (result.structured_content or {})

    asyncio.run(exercise())
    assert provider.calls == []


def test_supported_noul_criteria_reaches_provider() -> None:
    """Keep optional Noul criteria while rejecting unsupported question fields."""
    provider = RecordingProvider()
    server = create_mcp_server(provider)
    payload = arguments()
    definitions = payload["questions"]
    assert isinstance(definitions, dict)
    criteria = {"true": "Supported claim", "false": "Unsupported claim"}
    definitions["claim"]["criteria"] = criteria

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None, CallToolRequestParams(name="evaluate_policy", arguments=payload)
            )
            assert not result.is_error

    asyncio.run(exercise())
    assert len(provider.calls) == 1
    question = provider.calls[0][1]["claim"]
    assert isinstance(question, Noul)
    assert question.criteria == criteria
