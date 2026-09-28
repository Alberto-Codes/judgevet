"""Exercise strict media policy input through MCP SDK dispatch offline."""

import asyncio
import base64
import json
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from mcp.types import CallToolRequestParams

from judgevet.adapters.inbound.mcp import create_mcp_server
from judgevet.adapters.inbound.mcp_dispatch import ProviderDispatch
from judgevet.testing import FakeSystemOnePort
from tests.unit.test_cli_media import QUESTIONS, MediaProvider
from tests.unit.test_mcp_subprocess import environment, exchange, stop


def arguments() -> dict[str, object]:
    """Keep embedded evidence JSON text separate from SDK-owned outer parsing."""
    return {
        "state": {"record": ["exact", "state"]},
        "questions": QUESTIONS,
        "policy": {"rules": [{"question": "choice", "pass": {"choice": "yes"}}]},
        "evidence": json.dumps(
            {
                "images": [
                    {
                        "id": "first",
                        "data_base64": base64.b64encode(
                            b"\x00opaque-first\xff"
                        ).decode(),
                        "media_type": "image/png",
                    },
                    {
                        "id": "second",
                        "data_base64": base64.b64encode(
                            b"\xffopaque-second\x00"
                        ).decode(),
                        "media_type": "image/jpeg",
                    },
                ],
                "by_question": {"claim": ["second", "first"], "choice": ["first"]},
                "required": ["claim"],
            }
        ),
    }


@pytest.mark.parametrize(
    "outcome,fail", [("yes", False), ("insufficient_evidence", False), ("yes", True)]
)
def test_policy_media_preserves_submission(outcome: str, fail: bool) -> None:
    """Return preserved metadata while separating semantic and transport failure."""
    provider = MediaProvider(outcome=outcome, fail=fail)
    server = create_mcp_server(provider, model="selected-image-model")

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None,
                CallToolRequestParams(name="evaluate_policy", arguments=arguments()),
            )
            assert result.is_error is fail
            if fail:
                assert "ProviderTransportError" in result.content[0].text
                assert "policy" not in (result.structured_content or {})
            else:
                data = result.structured_content
                assert data["model"] == "resolved-image-model"
                assert data["usage"] == {"input_tokens": 0, "output_tokens": None}
                assert data["answers"]["choice"]["choice"] == outcome
                assert data["policy"]["result"] == (
                    "pass" if outcome == "yes" else "fail"
                )
                assert json.loads(result.content[0].text) == data

    asyncio.run(exercise())
    assert provider.text_calls == 0
    assert provider.closed == 0
    assert len(provider.calls) == 1
    state, questions, model, evidence = provider.calls[0]
    assert state == {"record": ["exact", "state"]}
    assert model == "selected-image-model"
    assert list(questions) == ["claim", "choice"]
    assert [(image.id, image.data, image.media_type) for image in evidence.images] == [
        ("first", b"\x00opaque-first\xff", "image/png"),
        ("second", b"\xffopaque-second\x00", "image/jpeg"),
    ]
    assert dict(evidence.by_question) == {
        "claim": ("second", "first"),
        "choice": ("first",),
    }
    assert evidence.required == frozenset({"claim"})


@pytest.mark.parametrize(
    "defect",
    [
        "decoded-object",
        "duplicate-key",
        "bad-base64",
        "unknown-reference",
        "missing-required",
        "extra-field",
    ],
)
def test_invalid_embedded_evidence_never_dispatches(defect: str) -> None:
    """Reject structural corruption instead of silently discarding evidence."""
    payload = arguments()
    text = payload["evidence"]
    assert isinstance(text, str)
    manifest = json.loads(text)
    if defect == "decoded-object":
        payload["evidence"] = manifest
    elif defect == "duplicate-key":
        payload["evidence"] = (
            '{"images":[],"by_question":{},"by_question":{"claim":[]}}'
        )
    else:
        if defect == "bad-base64":
            manifest["images"][0]["data_base64"] = "not base64!"
        elif defect == "unknown-reference":
            manifest["by_question"]["claim"] = ["absent"]
        elif defect == "missing-required":
            manifest = {"images": [], "by_question": {}, "required": ["claim"]}
        else:
            manifest["images"][0]["path"] = "must-not-read"
        payload["evidence"] = json.dumps(manifest)
    provider = MediaProvider()
    server = create_mcp_server(provider, model="selected-image-model")

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None, CallToolRequestParams(name="evaluate_policy", arguments=payload)
            )
            assert result.is_error
            assert "answers" not in (result.structured_content or {})
            if defect == "missing-required":
                assert "MissingEvidenceError" in result.content[0].text

    asyncio.run(exercise())
    assert provider.calls == []
    assert provider.text_calls == 0


def test_empty_embedded_evidence_keeps_text_call() -> None:
    """Preserve the old optional-empty text behavior through the media argument."""
    payload = arguments()
    payload["evidence"] = '{"images":[],"by_question":{}}'
    provider = MediaProvider()
    server = create_mcp_server(provider, model="selected-image-model")

    async def exercise() -> None:
        async with server.lifespan(server):
            result = await server._request_handlers["tools/call"].handler(
                None, CallToolRequestParams(name="evaluate_policy", arguments=payload)
            )
            assert not result.is_error
            assert result.structured_content["policy"]["result"] == "pass"

    asyncio.run(exercise())
    assert provider.text_calls == 1
    assert provider.calls == []


def test_media_work_drains_cancellation_off_loop() -> None:
    """Keep the loop responsive and skip a canceled queued media operation."""

    class BlockingProvider(MediaProvider):
        def __init__(self) -> None:
            super().__init__()
            self.started = threading.Event()
            self.release = threading.Event()
            self.threads: list[int] = []

        def system_one_media(self, state, questions, model, *, evidence):
            self.threads.append(threading.get_ident())
            self.started.set()
            if not self.release.wait(5):
                raise RuntimeError("event loop failed to release media operation")
            return super().system_one_media(state, questions, model, evidence=evidence)

    provider = BlockingProvider()
    lifecycle: list[int] = []

    @contextmanager
    def factory() -> Iterator[BlockingProvider]:
        lifecycle.append(threading.get_ident())
        try:
            yield provider
        finally:
            assert provider.release.is_set()
            lifecycle.append(threading.get_ident())
            provider.close()

    dispatch = ProviderDispatch(factory=factory)

    async def exercise() -> None:
        async with dispatch.session():
            owned_server = create_mcp_server(provider, model="selected-image-model")
            handler = owned_server._request_handlers["tools/call"].handler
            params = CallToolRequestParams(
                name="evaluate_policy", arguments=arguments()
            )
            running = asyncio.create_task(handler(None, params))
            try:
                assert await asyncio.to_thread(provider.started.wait, 2)
                assert not running.done()
                queued = asyncio.create_task(handler(None, params))
                await asyncio.sleep(0)
                queued.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await queued
                running.cancel()
                await asyncio.sleep(0.02)
                running.cancel()
                await asyncio.sleep(0.02)
                assert not running.done()
            finally:
                provider.release.set()
            with pytest.raises(asyncio.CancelledError):
                await running

    asyncio.run(exercise())
    assert len(provider.calls) == 1
    assert provider.threads == [provider.threads[0]]
    assert provider.threads[0] != threading.get_ident()
    assert lifecycle == [provider.threads[0], provider.threads[0]]
    assert provider.closed == 1


def test_media_schema_adds_only_optional_json_text() -> None:
    """Make the embedded JSON boundary discoverable without changing old tools."""
    server = create_mcp_server(MediaProvider(), model="selected-image-model")

    async def exercise() -> None:
        discovery = await server._request_handlers["tools/list"].handler(None, None)
        assert [tool.name for tool in discovery.tools] == [
            "ask_noul",
            "ask_choice",
            "ask_score",
            "evaluate_policy",
        ]
        policy = next(
            tool for tool in discovery.tools if tool.name == "evaluate_policy"
        )
        assert policy.input_schema["properties"]["evidence"]["type"] == "string"
        assert "evidence" not in policy.input_schema["required"]
        assert policy.input_schema["additionalProperties"] is False

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "defect",
    [
        "count",
        "image",
        "total",
        "text",
        "utf8",
        "nested-key",
        "nonfinite",
        "empty",
        "unicode",
        "required-shape",
    ],
)
def test_media_limits_and_strict_shapes(defect: str) -> None:
    """Reject actual limit violations before any provider inference."""
    payload = arguments()
    manifest = json.loads(str(payload["evidence"]))
    if defect in {"count", "image", "total"}:
        count = 17 if defect == "count" else 5 if defect == "total" else 1
        data = (
            b"x" * ((7 if defect == "total" else 8) * 1024 * 1024 + (defect == "image"))
            if defect != "count"
            else b"x"
        )
        encoded = base64.b64encode(data).decode()
        manifest["images"] = [
            {"id": str(i), "data_base64": encoded, "media_type": "image/png"}
            for i in range(count)
        ]
        manifest["by_question"] = {"claim": [str(i) for i in range(count)]}
    elif defect == "text":
        payload["evidence"] = " " * (48 * 1024 * 1024 + 1)
    elif defect == "utf8":
        payload["evidence"] = "é" * (24 * 1024 * 1024 + 1)
    elif defect == "nested-key":
        payload["evidence"] = '{"images":[],"by_question":{"claim":[],"claim":[]}}'
    elif defect == "nonfinite":
        payload["evidence"] = '{"images":[],"by_question":{},"required":NaN}'
    elif defect == "required-shape":
        manifest["required"] = {"claim": True}
    else:
        manifest["images"][0]["data_base64"] = "" if defect == "empty" else "éééé"
    if defect not in {"text", "utf8", "nested-key", "nonfinite"}:
        payload["evidence"] = json.dumps(manifest)
    provider = MediaProvider()
    server = create_mcp_server(provider, model="selected-image-model")

    async def exercise() -> None:
        result = await server._request_handlers["tools/call"].handler(
            None, CallToolRequestParams(name="evaluate_policy", arguments=payload)
        )
        assert result.is_error
        assert result.content[0].text == "ProviderRequestError: media evaluation failed"
        assert not result.structured_content

    asyncio.run(exercise())
    assert not provider.calls
    assert provider.text_calls == 0


def test_unsupported_media_provider_is_tool_error() -> None:
    """Refuse a text-only provider without producing fabricated answers."""
    provider = FakeSystemOnePort()
    server = create_mcp_server(provider)

    async def exercise() -> None:
        result = await server._request_handlers["tools/call"].handler(
            None, CallToolRequestParams(name="evaluate_policy", arguments=arguments())
        )
        assert result.is_error
        assert (
            result.content[0].text == "ProviderCapabilityError: media evaluation failed"
        )
        assert not result.structured_content

    asyncio.run(exercise())


@pytest.mark.e2e
def test_media_policy_over_actual_stdio() -> None:
    """Carry exact bytes through actual newline JSON-RPC and owned cleanup."""
    program = """
from contextlib import contextmanager
from judgevet.adapters.inbound.mcp_entrypoint import main
from tests.unit.test_cli_media import MediaProvider, QUESTIONS
provider = MediaProvider()
@contextmanager
def factory():
    try:
        yield provider
    finally:
        provider.close()
result = main(provider_factory=factory, model="selected-image-model")
assert provider.closed == 1
assert len(provider.calls) == 1
state, questions, model, evidence = provider.calls[0]
assert state == {"record": ["exact", "state"]}
assert model == "selected-image-model"
assert questions["claim"].instructions == QUESTIONS["claim"]["instructions"]
assert questions["choice"].instructions == QUESTIONS["choice"]["instructions"]
assert [(i.id, i.data, i.media_type) for i in evidence.images] == [
    ("first", bytes([0]) + b"opaque-first" + bytes([255]), "image/png"),
    ("second", bytes([255]) + b"opaque-second" + bytes([0]), "image/jpeg")]
assert dict(evidence.by_question) == {"claim": ("second", "first"), "choice": ("first",)}
assert evidence.required == frozenset({"claim"})
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
                    "clientInfo": {"name": "offline-media-test", "version": "1"},
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
                {"name": "evaluate_policy", "arguments": arguments()},
            )
            assert not result["isError"]
            data = result["structuredContent"]
            assert data["model"] == "resolved-image-model"
            assert data["usage"] == {"input_tokens": 0, "output_tokens": None}
            assert data["answers"]["choice"] == {
                "name": "choice",
                "type": "choice",
                "choice": "yes",
                "confidence": 0.8,
                "probabilities": {"yes": 1.0},
            }
            assert data["policy"]["result"] == "pass"
            assert json.loads(result["content"][0]["text"]) == data
            process.stdin.close()
            await process.stdin.wait_closed()
            await process.wait()
            assert process.stderr is not None
            diagnostic = await process.stderr.read()
            assert process.returncode == 0, diagnostic.decode()
        finally:
            await stop(process)

    asyncio.run(asyncio.wait_for(exercise(), 15))
