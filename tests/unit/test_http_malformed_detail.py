"""Keep synthetic malformed diagnostics from replacing typed HTTP errors.

Status and detail reference: https://docs.typesafe.ai/api.md. These are offline
fixtures, not observations of the live service.

Examples:
    ```bash
    uv run pytest tests/unit/test_http_malformed_detail.py
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Shared error translation.
"""

import asyncio

import httpx
import pytest

from judgevet.adapters.outbound.http import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
)
from judgevet.domain.errors import JevAuthError, JevRequestError

pytestmark = pytest.mark.unit
CANARY = "private-payload-canary"
MALFORMED = [
    [{"loc": None, "msg": "invalid", "type": "value_error"}],
    [{"loc": 42, "msg": "invalid", "type": "value_error"}],
    [{"loc": {"input": CANARY}, "msg": "invalid"}],
    [{"loc": [{"input": CANARY}], "msg": "invalid"}],
    [{"loc": "body", "msg": "invalid"}],
    [{"loc": [True], "msg": "invalid"}],
    [{"msg": {"input": CANARY}}],
    [{"type": [CANARY]}],
    [[{"input": CANARY}]],
    [CANARY],
    {"message": {"input": CANARY}},
    {"error_type": [CANARY], "message": "invalid"},
    {"message": 42},
    {"error_type": True},
    [{"type": "missing", "msg": "safe"}, {"loc": None}],
]
VALID = [
    ({"message": "Denied", "error_type": "auth"}, "auth: Denied"),
    ({"message": "Denied"}, "Denied"),
    ({"error_type": "auth"}, "auth"),
    (
        [{"type": "missing", "loc": ["body", 0], "msg": "Required", "input": CANARY}],
        "missing at body.0: Required",
    ),
    ([{"msg": "Required"}], "unknown_type: Required"),
    ([{}], "unknown_type: no message"),
    ([], ""),
    (None, ""),
    (CANARY, ""),
]


def translated(detail: object, status: int, asynchronous: bool) -> str:
    """Capture the typed error from either real adapter with a mock transport.

    Args:
        detail: Synthetic error diagnostic.
        status: HTTP status to translate.
        asynchronous: Select the async adapter.

    Returns:
        Safe rendered error text.
    """

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"detail": detail, "input": CANARY})

    transport = httpx.MockTransport(respond)

    async def call_async() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key=CANARY, transport=transport
        ) as port:
            await port.system_one(state=CANARY, questions={})

    expected = JevAuthError if status == 401 else JevRequestError
    with pytest.raises(expected) as caught:
        if asynchronous:
            asyncio.run(call_async())
        else:
            with HTTPSystemOneAdapter(api_key=CANARY, transport=transport) as port:
                port.system_one(state=CANARY, questions={})
    assert caught.value.status_code == status
    assert caught.value.retryable is False
    assert CANARY not in str(caught.value)
    assert CANARY not in repr(caught.value)
    return str(caught.value)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("status", [401, 422])
@pytest.mark.parametrize("detail", MALFORMED)
def test_malformed_detail_falls_back(
    detail: object, status: int, asynchronous: bool
) -> None:
    """Malformed diagnostics preserve typed status errors and status-only fallback."""
    message = translated(detail, status, asynchronous)
    assert message == translated(None, status, asynchronous)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("detail,expected", VALID)
def test_valid_detail_preserved(
    detail: object, expected: str, asynchronous: bool
) -> None:
    """Known object and validation-array diagnostics retain their safe rendering."""
    message = translated(detail, 422, asynchronous)
    baseline = translated(None, 422, asynchronous)
    assert message == (
        baseline.replace(" (status 422)", f"; {expected} (status 422)")
        if expected
        else baseline
    )
