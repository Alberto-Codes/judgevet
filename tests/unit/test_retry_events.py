"""Check terminal retry diagnostics without customer content."""

import httpx
import pytest
import structlog
from structlog.testing import capture_logs

from judgevet import HTTPSystemOneAdapter, JevServiceError, RetryPolicy
from tests.unit.test_http_retries import success


@pytest.mark.parametrize("transport_failure", [False, True])
def test_one_terminal_event(transport_failure: bool) -> None:
    """Report only the final attempt status after a recovered HTTP failure."""
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429)
        if transport_failure:
            raise httpx.ReadTimeout("diagnostic-canary", request=request)
        return success()

    previous = structlog.get_config()
    was_configured = structlog.is_configured()
    try:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10),
            cache_logger_on_first_use=False,
        )
        with (
            capture_logs() as events,
            HTTPSystemOneAdapter(
                api_key="credential-canary",
                transport=httpx.MockTransport(handle),
                retry=RetryPolicy(max_attempts=3, retry_base_delay=0),
            ) as adapter,
        ):
            if transport_failure:
                with pytest.raises(JevServiceError):
                    adapter.system_one("state-canary", {})
            else:
                adapter.system_one("state-canary", {})
        assert len(calls) == 2
        assert len(events) == 1
        assert events[0] == {
            "event": "http.call",
            "model": "jev-latest",
            "question_count": 0,
            "status_code": None if transport_failure else 200,
            "outcome": "error" if transport_failure else "success",
            "log_level": "debug",
        }
    finally:
        if was_configured:
            structlog.configure(**previous)
        else:
            structlog.reset_defaults()
