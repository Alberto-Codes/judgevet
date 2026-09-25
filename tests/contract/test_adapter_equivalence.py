"""Equivalence tests for sync and async HTTP adapters.

These tests verify that the sync (HTTPSystemOneAdapter) and async
(AsyncHTTPSystemOneAdapter) HTTP adapters produce identical outcomes when
driven by the same fixture.

This is NOT a second-implementation suite like test_adapter_contract.py.
That suite compares a fake (hand-built domain objects, no parse_system_one_response)
against the real adapter. This suite compares two real adapters: the sync
version is the oracle, the async version is under test.

Because both adapters share _parse_body and _translate_status_error,
this suite cannot detect regressions in those shared helpers — a shared-helper
change moves both adapters identically and the suite stays green. That is
the sync unit suite's and the existing contract suite's job. This suite's job
is the async-specific surface: the await-ed call path, the two except bodies,
and exception flow.

The equivalence suite's contract is: for every fixture, both adapters must
either both return a response or both raise an exception of the same type,
with matching status_code, retryable, message, and __cause__/__context__.
"""

from __future__ import annotations

import json
from typing import Any

import anyio
import httpx
import pytest

from judgevet import RetryPolicy
from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import JevError
from judgevet.domain.questions import Choice, Noul, Score
from judgevet.domain.response import SystemOneResponse

from .fixtures import get_fixtures
from .test_adapter_contract import _assert_responses_equal, _transport_for


def _call_sync(
    adapter: HTTPSystemOneAdapter, fixture: dict[str, Any]
) -> tuple[str, SystemOneResponse | JevError | httpx.HTTPStatusError]:
    """Call sync adapter and return outcome.

    Catches exactly (JevError, httpx.HTTPStatusError); anything else
    escapes and fails the test with the real traceback.

    Args:
        adapter: The sync HTTP adapter.
        fixture: The test fixture.

    Returns:
        ("ok", response) on success, ("err", exc) on exception.
    """
    try:
        response = adapter.system_one(
            state=fixture["request"]["state"],
            questions=fixture["request"]["questions"],
            model=fixture["request"]["model"],
        )
    except (JevError, httpx.HTTPStatusError) as exc:
        return ("err", exc)
    return ("ok", response)


def _call_async(
    adapter: AsyncHTTPSystemOneAdapter, fixture: dict[str, Any]
) -> tuple[str, SystemOneResponse | JevError | httpx.HTTPStatusError]:
    """Call async adapter and return outcome.

    Catches exactly (JevError, httpx.HTTPStatusError); anything else
    escapes and fails the test with the real traceback.

    Args:
        adapter: The async HTTP adapter.
        fixture: The test fixture.

    Returns:
        ("ok", response) on success, ("err", exc) on exception.
    """

    async def _run() -> tuple[
        str, SystemOneResponse | JevError | httpx.HTTPStatusError
    ]:
        async with adapter:
            try:
                response = await adapter.system_one(
                    state=fixture["request"]["state"],
                    questions=fixture["request"]["questions"],
                    model=fixture["request"]["model"],
                )
            except (JevError, httpx.HTTPStatusError) as exc:
                return ("err", exc)
            return ("ok", response)

    return anyio.run(_run)


def _assert_agree(
    fixture: dict[str, Any],
    expected: tuple[str, SystemOneResponse | JevError | httpx.HTTPStatusError],
    actual: tuple[str, SystemOneResponse | JevError | httpx.HTTPStatusError],
) -> None:
    """Assert that sync and async outcomes agree.

    Args:
        fixture: The test fixture (for name in failure messages).
        expected: Sync outcome.
        actual: Async outcome.
    """
    fixture_name = fixture["name"]

    # Outcome kind must match
    exp_kind, exp_val = expected
    act_kind, act_val = actual

    assert exp_kind == act_kind, (
        f"[{fixture_name}] Outcome kind mismatch: sync={exp_kind}, async={act_kind}"
    )

    if exp_kind == "ok":
        # Both returned responses — compare field-by-field
        assert isinstance(exp_val, SystemOneResponse)
        assert isinstance(act_val, SystemOneResponse)
        _assert_responses_equal(exp_val, act_val)
    else:
        # Both raised — compare exception details
        assert isinstance(exp_val, (JevError, httpx.HTTPStatusError))
        assert isinstance(act_val, (JevError, httpx.HTTPStatusError))

        # Same class by identity (same module, no aliasing)
        assert type(exp_val) is type(act_val), (
            f"[{fixture_name}] Exception type mismatch: "
            f"sync={type(exp_val).__name__}, "
            f"async={type(act_val).__name__}"
        )

        # Same status_code
        # JevError has status_code directly; httpx.HTTPStatusError has response.status_code
        exp_sc = getattr(exp_val, "status_code", None)
        if exp_sc is None and isinstance(exp_val, httpx.HTTPStatusError):
            exp_sc = exp_val.response.status_code
        act_sc = getattr(act_val, "status_code", None)
        if act_sc is None and isinstance(act_val, httpx.HTTPStatusError):
            act_sc = act_val.response.status_code
        assert exp_sc == act_sc, (
            f"[{fixture_name}] status_code mismatch: sync={exp_sc}, async={act_sc}"
        )

        # Same retryable (JevError only; httpx.HTTPStatusError has no retryable)
        if isinstance(exp_val, JevError) and isinstance(act_val, JevError):
            assert exp_val.retryable == act_val.retryable, (
                f"[{fixture_name}] retryable mismatch: "
                f"sync={exp_val.retryable}, "
                f"async={act_val.retryable}"
            )

        # Same str(exc)
        assert str(exp_val) == str(act_val), (
            f"[{fixture_name}] message mismatch: "
            f"sync={str(exp_val)!r}, "
            f"async={str(act_val)!r}"
        )

        # Same __cause__ None-ness and class
        exp_cause_is_none = exp_val.__cause__ is None
        act_cause_is_none = act_val.__cause__ is None
        assert exp_cause_is_none == act_cause_is_none, (
            f"[{fixture_name}] __cause__ None-ness mismatch: "
            f"sync={exp_cause_is_none}, "
            f"async={act_cause_is_none}"
        )
        if not exp_cause_is_none:
            assert (
                type(exp_val.__cause__).__name__ == type(act_val.__cause__).__name__
            ), (
                f"[{fixture_name}] __cause__ class mismatch: "
                f"sync={type(exp_val.__cause__).__name__}, "
                f"async={type(act_val.__cause__).__name__}"
            )

        # Same __context__ None-ness and class
        exp_context_is_none = exp_val.__context__ is None
        act_context_is_none = act_val.__context__ is None
        assert exp_context_is_none == act_context_is_none, (
            f"[{fixture_name}] __context__ None-ness mismatch: "
            f"sync={exp_context_is_none}, "
            f"async={act_context_is_none}"
        )
        if not exp_context_is_none:
            assert (
                type(exp_val.__context__).__name__ == type(act_val.__context__).__name__
            ), (
                f"[{fixture_name}] __context__ class mismatch: "
                f"sync={type(exp_val.__context__).__name__}, "
                f"async={type(act_val.__context__).__name__}"
            )


@pytest.mark.contract
@pytest.mark.parametrize("fixture", get_fixtures(), ids=lambda f: f["name"])
def test_adapters_agree(fixture: dict[str, Any]) -> None:
    """Test that sync and async adapters produce identical outcomes."""
    transport = _transport_for(fixture)
    sync_adapter = HTTPSystemOneAdapter(
        api_key="test-key", transport=transport, retry=RetryPolicy(max_attempts=1)
    )
    async_adapter = AsyncHTTPSystemOneAdapter(
        api_key="test-key", transport=transport, retry=RetryPolicy(max_attempts=1)
    )

    expected = _call_sync(sync_adapter, fixture)
    sync_adapter.close()
    actual = _call_async(async_adapter, fixture)

    _assert_agree(fixture, expected, actual)


@pytest.mark.contract
def test_3xx_fallthrough_agrees() -> None:
    """Test that 3xx fallthrough produces httpx.HTTPStatusError in both adapters.

    No fixture drives a 3xx, so this test builds its 302 inline.
    The shared _translate_status_error returns None for 3xx, so the raw
    httpx.HTTPStatusError must propagate.
    """
    status = 302
    body = {"redirecting": True}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status, json=body)

    transport = httpx.MockTransport(handler)

    sync_adapter = HTTPSystemOneAdapter(
        api_key="test-key", transport=transport, retry=RetryPolicy(max_attempts=1)
    )
    async_adapter = AsyncHTTPSystemOneAdapter(
        api_key="test-key", transport=transport, retry=RetryPolicy(max_attempts=1)
    )

    expected = _call_sync(
        sync_adapter,
        {"request": {"state": "x", "questions": {}, "model": "jev-1.13.0"}},
    )
    sync_adapter.close()
    actual = _call_async(
        async_adapter,
        {"request": {"state": "x", "questions": {}, "model": "jev-1.13.0"}},
    )

    # Both must raise httpx.HTTPStatusError (not JevError)
    assert expected[0] == "err"
    assert actual[0] == "err"
    assert type(expected[1]) is httpx.HTTPStatusError
    assert type(actual[1]) is httpx.HTTPStatusError

    exc_sync = expected[1]
    exc_async = actual[1]

    # Same status code (httpx.HTTPStatusError has response.status_code)
    assert exc_sync.response.status_code == exc_async.response.status_code == 302

    # __cause__ must be None (the 3xx fallthrough branch)
    assert exc_sync.__cause__ is None
    assert exc_async.__cause__ is None

    # __context__ must be None (the 3xx fallthrough branch)
    assert exc_sync.__context__ is None
    assert exc_async.__context__ is None


def test_adapters_handle_question_objects() -> None:
    """Test that adapters correctly convert Question objects to wire dicts.

    This test uses the contract test pattern: both adapters are driven with
    the same question objects, and the captured requests are compared. Since
    both adapters use the same _build_payload and wire_question,
    the requests must be byte-identical.
    """
    captured_sync: list[dict[str, Any]] = []
    captured_async: list[dict[str, Any]] = []

    def sync_handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        captured_sync.append(json.loads(body))
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": {},
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        )

    def async_handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8")
        captured_async.append(json.loads(body))
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "answers": {},
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        )

    transport_sync = httpx.MockTransport(sync_handler)
    transport_async = httpx.MockTransport(async_handler)

    sync_adapter = HTTPSystemOneAdapter(
        api_key="test-key",
        transport=transport_sync,
        retry=RetryPolicy(max_attempts=1),
    )
    async_adapter = AsyncHTTPSystemOneAdapter(
        api_key="test-key",
        transport=transport_async,
        retry=RetryPolicy(max_attempts=1),
    )

    # Use bare Noul without criteria to test the omission rule
    noul_no_criteria = Noul(instructions="Is this valid?")
    noul_with_criteria = Noul(
        instructions="Is this correct?",
        criteria={"true": "Correct", "false": "Incorrect"},
    )
    choice = Choice(
        criteria={"a": "Option A", "b": "Option B"},
        instructions="Choose one:",
    )
    score = Score(
        criteria=["Poor", "Fair", "Good", "Excellent"],
        instructions="Rate quality:",
    )

    # Call sync adapter
    sync_adapter.system_one(
        state="Test content",
        questions={
            "bare_noul": noul_no_criteria,
            "noul": noul_with_criteria,
            "choice": choice,
            "score": score,
        },
    )
    sync_adapter.close()

    # Call async adapter
    anyio.run(
        async_adapter.system_one,
        "Test content",
        {
            "bare_noul": noul_no_criteria,
            "noul": noul_with_criteria,
            "choice": choice,
            "score": score,
        },
    )

    # Both adapters must produce identical requests
    assert len(captured_sync) == 1
    assert len(captured_async) == 1
    assert captured_sync[0] == captured_async[0]

    questions = captured_sync[0]["questions"]

    # Bare Noul without criteria (inferred: None keys are omitted)
    assert questions["bare_noul"] == {
        "type": "noul",
        "instructions": "Is this valid?",
    }

    # Noul with criteria
    assert questions["noul"] == {
        "type": "noul",
        "instructions": "Is this correct?",
        "criteria": {"true": "Correct", "false": "Incorrect"},
    }

    # Choice with criteria
    assert questions["choice"] == {
        "type": "choice",
        "instructions": "Choose one:",
        "criteria": {"a": "Option A", "b": "Option B"},
    }

    # Score with criteria (note: criteria is a list, not dict)
    assert questions["score"] == {
        "type": "score",
        "instructions": "Rate quality:",
        "criteria": ["Poor", "Fair", "Good", "Excellent"],
    }
