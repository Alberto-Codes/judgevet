"""Acceptance for malformed answers crossing parser and both HTTP boundaries.

Examples:
    ```python
    from tests.answer_validation_support import answer_payload, response_payload
    from judgevet.domain.response_parser import parse_system_one_response

    response = parse_system_one_response(
        "fixture", response_payload(answer_payload("noul"))
    )
    assert response.answers["q"].noul == 0.5
    ```

See Also:
    - [judgevet.domain.response_parser][]: Shared parser
    - [judgevet.adapters.outbound.http][]: Sync and async adapters
"""

import asyncio
import json
import re
import traceback
from typing import Any

import httpx
import pytest

from judgevet import Answer, JevResponseError, NoulAnswer, RetryPolicy
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain import response_parser
from tests.answer_validation_support import (
    FIELDS,
    MALFORMED_ANSWERS,
    answer_payload,
    construct_answer,
    numeric_payload,
    response_payload,
)

pytestmark = pytest.mark.unit


def assert_response_error(error: JevResponseError) -> None:
    assert error.status_code == 200
    assert error.retryable is False
    assert re.search(r"\bq\b", str(error)) is not None


@pytest.mark.parametrize("raw", MALFORMED_ANSWERS)
def test_parser_rejects_invalid_answers(raw: dict[str, Any]) -> None:
    with pytest.raises(JevResponseError) as caught:
        response_parser.parse_system_one_response("fixture", response_payload(raw))
    assert_response_error(caught.value)


@pytest.mark.parametrize("kind,field", FIELDS)
@pytest.mark.parametrize("value", [0, 1, 0.0, -0.0, 1.0, 0.25])
def test_parser_preserves_valid_answers(kind: str, field: str, value: float) -> None:
    raw = numeric_payload(kind, field, value)
    response = response_parser.parse_system_one_response(
        "fixture", response_payload(raw)
    )
    assert response.answers["q"] == construct_answer(raw)


@pytest.mark.parametrize("raw", MALFORMED_ANSWERS)
@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
def test_http_rejects_invalid_answers_without_retry(
    raw: dict[str, Any], asynchronous: bool
) -> None:
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        # Raw bytes allow synthetic NaN/Infinity to reach the response decoder.
        return httpx.Response(200, content=json.dumps(response_payload(raw)))

    retry = RetryPolicy(max_attempts=3, retry_base_delay=0, retry_transport=True)
    transport = httpx.MockTransport(handle)

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic", transport=transport, retry=retry
        ) as adapter:
            with pytest.raises(JevResponseError) as caught:
                await adapter.system_one(
                    "synthetic state", {"q": {"type": raw["type"]}}
                )
            assert_response_error(caught.value)

    if asynchronous:
        asyncio.run(run())
    else:
        with HTTPSystemOneAdapter(
            api_key="synthetic", transport=transport, retry=retry
        ) as adapter:
            with pytest.raises(JevResponseError) as caught:
                adapter.system_one("synthetic state", {"q": {"type": raw["type"]}})
            assert_response_error(caught.value)
    assert len(calls) == 1


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
def test_http_preserves_valid_mixed_answers(asynchronous: bool) -> None:
    answers = {kind: answer_payload(kind) for kind in ("noul", "choice", "score")}
    raw = dict(response_payload(answer_payload("noul")), answers=answers)

    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=raw)

    transport = httpx.MockTransport(handle)

    async def run() -> dict[str, Answer]:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic", transport=transport
        ) as adapter:
            return (await adapter.system_one("synthetic", {})).answers

    if asynchronous:
        parsed = asyncio.run(run())
    else:
        with HTTPSystemOneAdapter(api_key="synthetic", transport=transport) as adapter:
            parsed = adapter.system_one("synthetic", {}).answers
    assert parsed == {
        kind: construct_answer(answer) for kind, answer in answers.items()
    }


def test_translation_diagnostic_is_bounded_and_omits_values() -> None:
    marker = "synthetic-private-value"
    raw = dict(answer_payload("choice"), choice=marker)
    with pytest.raises(JevResponseError) as caught:
        response_parser.parse_system_one_response(
            "fixture", response_payload(raw, "q" * 5000)
        )
    rendered = "".join(traceback.format_exception_only(caught.value))
    assert marker not in rendered
    assert len(rendered) < 250
    assert "choice" in rendered
    assert "qqqq" in rendered
    assert caught.value.__suppress_context__ is True
    assert caught.value.__cause__ is None


def test_parser_does_not_hide_programming_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_constructor(noul: float) -> NoulAnswer:
        raise RuntimeError("synthetic programming failure")

    monkeypatch.setattr(response_parser, "NoulAnswer", broken_constructor)
    with pytest.raises(RuntimeError, match="synthetic programming failure"):
        response_parser.parse_system_one_response(
            "fixture", response_payload(answer_payload("noul"))
        )
