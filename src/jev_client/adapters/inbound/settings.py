"""The one ``Settings`` the composition roots read from the environment.

``Settings`` nests ``ApiSettings`` under ``api``. pydantic-settings splits the
environment on ``__``, so ``JEV_API__BASE_URL`` and ``JEV_API__KEY`` reach the
nested model. The key also answers to ``TYPESAFE_API_KEY``, which is the name
the published Jev documentation and every other client use.

Nothing else under ``src/`` subclasses ``BaseSettings``. An adapter takes its
configuration as arguments; only a composition root reads the environment.
That is what keeps the outbound adapter testable without touching
``os.environ``.

The key is a ``SecretStr``. Its ``repr`` renders as ``**********``, so a
traceback or a log line that carries the settings object does not carry the
key.

Attributes:
    ApiSettings: Base URL, key and default model for the Jev API.
    Settings: The root model.

Examples:
    ```python
    settings = Settings()
    adapter = HTTPSystemOneAdapter(
        api_key=settings.api.key.get_secret_value() if settings.api.key else None,
        base_url=settings.api.base_url,
    )
    ```

See Also:
    - [jev_client.adapters.outbound.http][]: Takes the values, never the environment.
    - [jev_client.adapters.inbound.cli][]: Reads it once per process.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-latest"


class ApiSettings(BaseSettings):
    """Connection settings for the Jev API.

    Attributes:
        base_url (str): Root of the Jev API. Defaults to the documented host.
        key (SecretStr | None): The API key. ``None`` until one is supplied,
            which is why every call path reports a missing key rather than
            assuming one.
        default_model (str): Model id sent when a call names none.

    Examples:
        ```python
        api = ApiSettings()
        assert api.base_url == "https://api.typesafe.ai"
        ```

    See Also:
        - [jev_client.adapters.inbound.settings.Settings][]: Nests this model.
    """

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    base_url: str = Field(
        default=DEFAULT_BASE_URL,
        validation_alias=AliasChoices("base_url", "TYPESAFE_BASE_URL"),
    )
    key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("key", "TYPESAFE_API_KEY"),
    )
    default_model: str = Field(default=DEFAULT_MODEL)


class Settings(BaseSettings):
    """Every setting this client reads, nested per adapter.

    Attributes:
        api (ApiSettings): Base URL, key and default model for the Jev API.

    Examples:
        ```python
        settings = Settings()
        print(settings.api.base_url)
        ```

    See Also:
        - [jev_client.adapters.inbound.settings.ApiSettings][]: The nested model.
    """

    model_config = SettingsConfigDict(
        env_prefix="JEV_",
        env_nested_delimiter="__",
        extra="ignore",
        frozen=True,
    )

    api: ApiSettings = Field(default_factory=ApiSettings)
