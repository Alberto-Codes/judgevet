"""Exercise typed callers using only the supported root imports."""

from typing import assert_type

import anyio
import httpx

from judgevet import (
    Answer,
    AsyncHTTPSystemOneAdapter,
    AsyncSystemOnePort,
    HTTPSystemOneAdapter,
    Noul,
    NoulAnswer,
    Question,
    SystemOnePort,
    SystemOneResponse,
    Usage,
)
from tests.cli_process_support import SUCCESS


def _call(port: SystemOnePort) -> SystemOneResponse:
    question: Question = Noul(instructions="True?")
    return port.system_one("content", {"noul": question}, "jev-latest")


async def _call_async(port: AsyncSystemOnePort) -> SystemOneResponse:
    question: Question = Noul(instructions="True?")
    return await port.system_one("content", {"noul": question}, "jev-latest")


def _assert_answer_types(response: SystemOneResponse) -> None:
    assert_type(response.answers["noul"], Answer)
    assert_type(response.nouls["noul"], NoulAnswer)
    assert_type(response.usage, Usage)
    assert response.nouls["noul"].noul == 0.42


def _reply(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=SUCCESS)


def test_sync_root_typed_caller() -> None:
    with HTTPSystemOneAdapter(
        api_key="test-key", transport=httpx.MockTransport(_reply)
    ) as adapter:
        _assert_answer_types(_call(adapter))


def test_async_root_typed_caller() -> None:
    async def exercise() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="test-key", transport=httpx.MockTransport(_reply)
        ) as adapter:
            _assert_answer_types(await _call_async(adapter))

    anyio.run(exercise)
