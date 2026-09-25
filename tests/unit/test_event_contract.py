"""Pin built-in event fields, metadata privacy and configured rendering."""

import io
import json
import logging
from collections.abc import Iterator

import httpx
import pytest
import structlog

import judgevet
from judgevet.adapters.inbound.logs import LogSettings, configure, configure_mcp_logging
from tests.cli_process_support import SUCCESS

HTTP_FIELDS = {
    "event",
    "level",
    "timestamp",
    "model",
    "question_count",
    "status_code",
    "outcome",
    "resolved_model",
    "input_tokens",
    "output_tokens",
    "request_id",
}


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    """Install the real JSON processor chain and restore the caller's setup."""
    previous = structlog.get_config()
    was_configured = structlog.is_configured()
    output = io.StringIO()
    configure(LogSettings(format="json", level="debug"), output)
    try:
        yield output
    finally:
        if was_configured:
            structlog.configure(**previous)
        else:
            structlog.reset_defaults()


def call(model: str = "jev-latest", resolved: str = "jev-1.13.0") -> None:
    """Exercise the real sync adapter against a synthetic typed response."""
    payload = {**SUCCESS, "model": resolved}
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=payload)

    with judgevet.HTTPSystemOneAdapter(
        api_key="credential-canary",
        transport=httpx.MockTransport(respond),
    ) as adapter:
        response = adapter.system_one(
            "state-canary",
            {"question-key-canary": judgevet.Noul(instructions="question-canary")},
            model,
        )
    assert response.model == resolved
    assert requests[0]["model"] == model


def last_event(stream: io.StringIO) -> dict:
    """Decode the last actually rendered event."""
    return json.loads(stream.getvalue().splitlines()[-1])


def test_success_schema(stream: io.StringIO) -> None:
    """Render exact metadata from the successful typed response."""
    call()
    event = last_event(stream)
    assert set(event) == HTTP_FIELDS
    assert (
        event.items()
        >= {
            "event": "http.call",
            "level": "debug",
            "model": "jev-latest",
            "resolved_model": "jev-1.13.0",
            "question_count": 1,
            "status_code": 200,
            "outcome": "success",
            "input_tokens": 3,
            "output_tokens": 2,
            "request_id": None,
        }.items()
    )


def test_builtin_context_is_filtered_but_application_context_survives(stream) -> None:
    """Drop bound customer data only from the reserved built-in vocabulary."""
    with structlog.contextvars.bound_contextvars(
        state="context-canary",
        tenant="tenant-canary",
        api_key="credential-canary",
        command="command-canary",
        run_id="run-canary",
    ):
        call()
        diagnostic = last_event(stream)
        assert set(diagnostic) == HTTP_FIELDS
        assert "canary" not in json.dumps(diagnostic)
        structlog.get_logger().info("application.event")
        application = last_event(stream)
        assert application["tenant"] == "tenant-canary"
        assert application["api_key"] == "***"


@pytest.mark.parametrize(
    "value", ["model-canary", "jev-1.2.3\ncanary", "jev-" + "1" * 70 + ".2.3"]
)
def test_model_values_are_filtered_without_changing_response(stream, value) -> None:
    """Do not copy arbitrary requested or resolved model strings into events."""
    call(value, value)
    event = last_event(stream)
    assert event["model"] is None
    assert event["resolved_model"] is None
    assert value not in stream.getvalue()


def test_missing_usage_is_null(stream) -> None:
    """Keep token counts null when missing usage prevents typed parsing."""
    payload = {**SUCCESS, "usage": {}}
    with (
        judgevet.HTTPSystemOneAdapter(
            api_key="credential-canary",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=payload)
            ),
        ) as adapter,
        pytest.raises(judgevet.JevResponseError),
    ):
        adapter.system_one("state-canary", {})
    event = last_event(stream)
    assert event["input_tokens"] is None
    assert event["output_tokens"] is None
    assert event["resolved_model"] is None
    assert event["outcome"] == "error"


def test_mcp_runtime_uses_only_dedicated_correlation(stream) -> None:
    """Ignore SDK text and arbitrary bound fields while forwarding severity."""
    logger = logging.getLogger("mcp")
    previous = logger.handlers[:], logger.propagate, logger.level
    try:
        configure_mcp_logging()
        with (
            judgevet.bind_request_id("req-mcp"),
            structlog.contextvars.bound_contextvars(state="context-canary"),
        ):
            logger.error("sdk-canary")
        event = last_event(stream)
        assert set(event) == {"event", "level", "timestamp", "request_id"}
        assert event["request_id"] == "req-mcp"
        assert event["event"] == "mcp.runtime"
        assert event["level"] == "error"
        assert "canary" not in stream.getvalue()
    finally:
        logger.handlers, logger.propagate, logger.level = previous
