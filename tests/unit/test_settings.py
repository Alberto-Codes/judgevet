"""Unit tests for Settings class."""

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
