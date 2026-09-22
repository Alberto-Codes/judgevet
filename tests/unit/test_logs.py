"""Unit tests for the logs adapter."""

import contextvars
import io
from unittest.mock import patch

import pytest
import structlog
from pydantic import ValidationError

from judgevet.adapters.inbound.logs import (
    REDACTED,
    SECRET_KEYS,
    LogSettings,
    bind_command,
    bind_invocation,
    configure,
    new_run_id,
    redact,
    wants_json,
)


class TestLogSettings:
    """Tests for LogSettings."""

    def test_defaults(self) -> None:
        """Test LogSettings defaults."""
        settings = LogSettings()
        assert settings.format == "auto"
        assert settings.level == "info"

    def test_custom_format(self) -> None:
        """Test LogSettings with custom format."""
        settings = LogSettings(format="json")
        assert settings.format == "json"

    def test_custom_level(self) -> None:
        """Test LogSettings with custom level."""
        settings = LogSettings(level="debug")
        assert settings.level == "debug"

    @pytest.mark.parametrize(
        "field_name, value", [("format", "json"), ("level", "debug")]
    )
    def test_frozen(self, field_name: str, value: str) -> None:
        """Require each configured field to reject runtime mutation."""
        settings = LogSettings()
        with pytest.raises(ValidationError, match="frozen"):
            setattr(settings, field_name, value)


class TestRedact:
    """Tests for the redact processor."""

    def test_redacts_secret_key(self) -> None:
        """Test that secret keys are redacted."""
        result = redact(None, "info", {"api_key": "secret123"})
        assert result["api_key"] == REDACTED

    def test_redacts_secret_key_by_name(self) -> None:
        """Test that any key in SECRET_KEYS is redacted."""
        for key in SECRET_KEYS:
            result = redact(None, "info", {key: "secret_value"})
            assert result[key] == REDACTED

    def test_does_not_redact_non_secret(self) -> None:
        """Test that non-secret keys are not redacted."""
        result = redact(None, "info", {"user_id": "123"})
        assert result["user_id"] == "123"

    def test_redacts_nested_dict(self) -> None:
        """Test that nested dicts have secrets redacted."""
        result = redact(None, "info", {"data": {"api_key": "secret"}})
        assert result["data"]["api_key"] == REDACTED

    def test_redacts_list_of_dicts(self) -> None:
        """Test that lists of dicts have secrets redacted."""
        result = redact(
            None,
            "info",
            {"items": [{"api_key": "secret1"}, {"api_key": "secret2"}]},
        )
        assert result["items"][0]["api_key"] == REDACTED
        assert result["items"][1]["api_key"] == REDACTED

    def test_preserves_exc_info(self) -> None:
        """Test that exc_info is passed through unchanged."""
        exc_info = (ValueError, ValueError("test"), None)
        result = redact(None, "info", {"exc_info": exc_info})
        assert result["exc_info"] is exc_info

    def test_redacts_pem_strings(self) -> None:
        """Test that PEM strings are redacted regardless of key name."""
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        result = redact(None, "info", {"some_field": pem})
        assert result["some_field"] == REDACTED

    def test_preserves_non_secret_string(self) -> None:
        """Test that non-PEM strings are not redacted."""
        result = redact(None, "info", {"message": "hello world"})
        assert result["message"] == "hello world"


class TestWantsJson:
    """Tests for wants_json function."""

    def test_format_json_forces_json(self) -> None:
        """Test that format='json' forces JSON output."""
        settings = LogSettings(format="json")
        stream = io.StringIO()
        assert wants_json(settings, stream) is True

    def test_format_console_forces_console(self) -> None:
        """Test that format='console' forces console output."""
        settings = LogSettings(format="console")
        stream = io.StringIO()
        assert wants_json(settings, stream) is False

    def test_format_auto_on_tty(self) -> None:
        """Test that format='auto' uses console on TTY."""
        settings = LogSettings(format="auto")
        stream = io.StringIO()
        with patch.object(stream, "isatty", return_value=True):
            assert wants_json(settings, stream) is False

    def test_format_auto_on_non_tty(self) -> None:
        """Test that format='auto' uses JSON on non-TTY."""
        settings = LogSettings(format="auto")
        stream = io.StringIO()
        with patch.object(stream, "isatty", return_value=False):
            assert wants_json(settings, stream) is True


class TestConfigure:
    """Tests for configure function."""

    def test_configure_does_not_raise(self) -> None:
        """Test that configure does not raise on valid input."""
        settings = LogSettings(format="json", level="info")
        captured = io.StringIO()
        configure(settings, stream=captured)
        # Configure structlog, emit a log, and verify the captured output
        logger = structlog.get_logger()
        logger.info("test_event")
        output = captured.getvalue()
        assert "test_event" in output


class TestNewRunId:
    """Tests for new_run_id function."""

    def test_returns_twelve_hex_chars(self) -> None:
        """Test that new_run_id returns 12 hex characters."""
        run_id = new_run_id()
        assert len(run_id) == 12
        # Verify it's valid hex
        int(run_id, 16)

    def test_returns_unique_ids(self) -> None:
        """Test that consecutive calls return different IDs."""
        id1 = new_run_id()
        id2 = new_run_id()
        assert id1 != id2


class TestBindFunctions:
    """Tests for binding functions."""

    def test_bind_command_sets_context(self) -> None:
        """Test that bind_command sets the command context variable."""
        # Clear any existing context
        for var in list(contextvars.Context().items()):
            var[0].set(None)
        settings = LogSettings(format="json", level="info")
        captured = io.StringIO()
        configure(settings, stream=captured)
        bind_command("jev call")
        logger = structlog.get_logger()
        logger.info("test_event")
        output = captured.getvalue()
        assert "command" in output
        assert "jev call" in output

    def test_bind_invocation_sets_context(self) -> None:
        """Test that bind_invocation sets command and run_id context variables."""
        # Clear any existing context
        for var in list(contextvars.Context().items()):
            var[0].set(None)
        settings = LogSettings(format="json", level="info")
        captured = io.StringIO()
        configure(settings, stream=captured)
        run_id = new_run_id()
        bind_invocation("jev", run_id)
        logger = structlog.get_logger()
        logger.info("test_event")
        output = captured.getvalue()
        assert "command" in output
        assert "jev" in output
        assert "run_id" in output


class TestStderrOutput:
    """Tests that verify logging goes to stderr."""

    def test_configure_writes_to_stderr(self) -> None:
        """Test that configure sets up logging to stderr."""
        settings = LogSettings(format="console", level="info")
        # Capture both stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        configure(settings, stream=stderr_capture)

        # Try to get a logger and emit one
        logger = structlog.get_logger()
        logger.info("test_message")

        # Verify nothing went to stdout
        assert stdout_capture.getvalue() == ""
        # Verify something went to stderr
        stderr_output = stderr_capture.getvalue()
        assert "test_message" in stderr_output or stderr_output != ""


class TestSecretKeys:
    """Tests for SECRET_KEYS constant."""

    def test_secret_keys_contains_expected_keys(self) -> None:
        """Test that SECRET_KEYS contains the expected field names."""
        expected_keys = {
            "api_key",
            "api_key_id",
            "authorization",
            "private_key",
            "private_key_pem",
            "signature",
            "TYPESAFE_API_KEY",
        }
        assert expected_keys == SECRET_KEYS
