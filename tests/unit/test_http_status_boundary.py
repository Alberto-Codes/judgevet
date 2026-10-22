"""Keep non-success HTTP status exceptions behind the typed adapter boundary.

HTTPX2 status exceptions come from Response.raise_for_status.
Source: https://pydantic.dev/docs/httpx2/api/exceptions/.
All response statuses here are synthetic, not live-service evidence.

Examples:
    ```python
    from judgevet import JevError

    assert issubclass(JevError, Exception)
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Both adapter call paths.
    - [judgevet.adapters.outbound.response_translation][]: Status mapping.
"""

import httpx2
import pytest

from judgevet import AsyncHTTPSystemOneAdapter, HTTPSystemOneAdapter, JevError
from judgevet.adapters.outbound.retries import RetryPolicy

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("status", [100, 199, 301, 302, 304, 308])
def test_sync_status_errors_are_typed(status: int) -> None:
    calls: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        calls.append(str(request.url))
        return httpx2.Response(status, headers={"Location": "https://example.invalid/"})

    with (
        HTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx2.MockTransport(respond),
            retry=RetryPolicy(max_attempts=1),
        ) as adapter,
        pytest.raises(JevError) as caught,
    ):
        adapter.system_one("synthetic", {})
    assert caught.value.status_code == status
    assert isinstance(caught.value.__cause__, httpx2.HTTPStatusError)
    assert caught.value.__cause__.response.status_code == status
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [100, 199, 301, 302, 304, 308])
async def test_async_status_errors_are_typed(status: int) -> None:
    calls: list[str] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        calls.append(str(request.url))
        return httpx2.Response(status, headers={"Location": "https://example.invalid/"})

    async with AsyncHTTPSystemOneAdapter(
        api_key="synthetic",
        transport=httpx2.MockTransport(respond),
        retry=RetryPolicy(max_attempts=1),
    ) as adapter:
        with pytest.raises(JevError) as caught:
            await adapter.system_one("synthetic", {})
    assert caught.value.status_code == status
    assert isinstance(caught.value.__cause__, httpx2.HTTPStatusError)
    assert caught.value.__cause__.response.status_code == status
    assert len(calls) == 1
