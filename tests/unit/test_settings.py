"""Unit tests for Settings class."""

import pytest

from judgevet.adapters.inbound.logs import redact
from judgevet.adapters.inbound.settings import Settings


class TestSettingsDefaults:
    """Tests for Settings defaults with no environment."""

    def test_defaults_no_env(self, monkeypatch) -> None:
        """Test Settings with no environment variables set."""
        # Ensure no relevant env vars are set
        monkeypatch.delenv("JEV_API__KEY", raising=False)
        monkeypatch.delenv("JEV_API__BASE_URL", raising=False)
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)

        settings = Settings()

        assert settings.api.base_url == "https://api.typesafe.ai"
        assert settings.api.key is None
        assert settings.api.default_model == "jev-latest"

    def test_jev_api_key_env(self, monkeypatch) -> None:
        """Test Settings with JEV_API__KEY environment variable."""
        monkeypatch.setenv("JEV_API__KEY", "test-key-from-env")
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)

        settings = Settings()

        assert settings.api.key is not None
        assert settings.api.key.get_secret_value() == "test-key-from-env"

    def test_typesafe_api_key_alias(self, monkeypatch) -> None:
        """Test Settings with TYPESAFE_API_KEY environment variable as alias."""
        monkeypatch.setenv("TYPESAFE_API_KEY", "typesafe-key")
        monkeypatch.delenv("JEV_API__KEY", raising=False)

        settings = Settings()

        assert settings.api.key is not None
        assert settings.api.key.get_secret_value() == "typesafe-key"

    def test_jev_api_base_url(self, monkeypatch) -> None:
        """Test Settings with JEV_API__BASE_URL environment variable."""
        monkeypatch.setenv("JEV_API__BASE_URL", "https://custom.api.example.com")
        monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)

        settings = Settings()

        assert settings.api.base_url == "https://custom.api.example.com"

    def test_repr_key_not_exposed(self, monkeypatch) -> None:
        """Test that repr(settings.api.key) never contains the key."""
        monkeypatch.setenv("JEV_API__KEY", "secret-api-key-12345")
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)

        settings = Settings()

        key_repr = repr(settings.api.key)
        assert "secret-api-key-12345" not in key_repr
        assert "secret-api-key-12345" not in repr(settings)
        # SecretStr repr should be something like SecretStr('**********')
        assert "**********" in key_repr or "****" in key_repr


class TestSettingsEnvironmentPriority:
    """Tests for Settings environment variable priority."""

    def test_jev_api_key_over_typesafe_alias(self, monkeypatch) -> None:
        """Test that JEV_API__KEY takes precedence over TYPESAFE_API_KEY."""
        monkeypatch.setenv("JEV_API__KEY", "jev-key-preferred")
        monkeypatch.setenv("TYPESAFE_API_KEY", "typesafe-key-ignored")

        settings = Settings()

        assert settings.api.key is not None
        assert settings.api.key.get_secret_value() == "jev-key-preferred"


class TestSettingsBaseUrlValidation:
    """Tests for base_url scheme validation."""

    def test_https_accepted(self, monkeypatch) -> None:
        """Test that https:// URLs are accepted."""
        monkeypatch.setenv("JEV_API__BASE_URL", "https://api.typesafe.ai")
        monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)

        settings = Settings()

        assert settings.api.base_url == "https://api.typesafe.ai"

    def test_remote_http_rejected(self, monkeypatch) -> None:
        """Test that remote http:// URLs are rejected."""
        monkeypatch.setenv("JEV_API__BASE_URL", "http://evil.example")
        monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)

        with pytest.raises(ValueError) as exc_info:
            Settings()

        assert "JEV_API__BASE_URL" in str(exc_info.value)
        assert "plaintext HTTP" in str(exc_info.value)

    def test_localhost_http_accepted(self, monkeypatch) -> None:
        """Test that http://localhost is accepted."""
        monkeypatch.setenv("JEV_API__BASE_URL", "http://localhost")
        monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)

        settings = Settings()

        assert settings.api.base_url == "http://localhost"

    def test_127_0_0_1_http_accepted(self, monkeypatch) -> None:
        """Test that http://127.0.0.1 is accepted."""
        monkeypatch.setenv("JEV_API__BASE_URL", "http://127.0.0.1")
        monkeypatch.delenv("TYPESAFE_BASE_URL", raising=False)

        settings = Settings()

        assert settings.api.base_url == "http://127.0.0.1"

    def test_typesafe_base_url_https_accepted(self, monkeypatch) -> None:
        """Test that TYPESAFE_BASE_URL with https:// is accepted."""
        monkeypatch.setenv("TYPESAFE_BASE_URL", "https://custom.api.example.com")
        monkeypatch.delenv("JEV_API__BASE_URL", raising=False)

        settings = Settings()

        assert settings.api.base_url == "https://custom.api.example.com"

    def test_typesafe_base_url_remote_http_rejected(self, monkeypatch) -> None:
        """Test that TYPESAFE_BASE_URL with remote http:// is rejected."""
        monkeypatch.setenv("TYPESAFE_BASE_URL", "http://evil.example")
        monkeypatch.delenv("JEV_API__BASE_URL", raising=False)

        with pytest.raises(ValueError) as exc_info:
            Settings()

        assert "JEV_API__BASE_URL" in str(exc_info.value)
        assert "plaintext HTTP" in str(exc_info.value)


class TestSettingsWithLog:
    """Tests for Settings with log configuration."""

    def test_log_defaults(self, monkeypatch) -> None:
        """Test Settings with default log configuration."""
        monkeypatch.delenv("JEV_LOG__FORMAT", raising=False)
        monkeypatch.delenv("JEV_LOG__LEVEL", raising=False)

        settings = Settings()

        assert settings.log.format == "auto"
        assert settings.log.level == "info"

    def test_log_format_env(self, monkeypatch) -> None:
        """Test Settings with JEV_LOG__FORMAT environment variable."""
        monkeypatch.setenv("JEV_LOG__FORMAT", "json")
        monkeypatch.delenv("JEV_LOG__LEVEL", raising=False)

        settings = Settings()

        assert settings.log.format == "json"

    def test_log_level_env(self, monkeypatch) -> None:
        """Test Settings with JEV_LOG__LEVEL environment variable."""
        monkeypatch.setenv("JEV_LOG__LEVEL", "debug")
        monkeypatch.delenv("JEV_LOG__FORMAT", raising=False)

        settings = Settings()

        assert settings.log.level == "debug"

    def test_log_redacts_secret_keys(self, monkeypatch) -> None:
        """Test that log redact function works with api_key."""
        monkeypatch.setenv("JEV_API__KEY", "test-key")

        # Test that api_key is redacted
        result = redact(None, "info", {"api_key": "secret123"})
        assert result["api_key"] == "***"
