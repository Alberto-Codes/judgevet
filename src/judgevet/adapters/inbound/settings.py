"""Configure credential sources, connection options and logging without IO.

``Settings`` nests ``ApiSettings`` and ``LogSettings`` under ``api`` and
``log`` respectively. pydantic-settings splits the environment on ``__``, so
``JEV_API__BASE_URL`` and ``JEV_LOG__LEVEL`` reach the nested models.

Nothing else under ``src/`` subclasses ``BaseSettings``. An adapter takes its
configuration as arguments; only a composition root reads the environment.
That is what keeps the outbound adapter testable without touching
``os.environ``.

The configured key or command is a ``SecretStr``. File and command sources
resolve only when ``resolve_key`` is called, not during Settings construction.
Its ``repr`` renders as ``**********``, so a
traceback or a log line that carries the settings object does not carry the
key.

``ApiSettings`` validates ``base_url`` to prevent plaintext HTTP to remote
hosts. Only ``https://`` or loopback ``http://localhost`` and ``http://127.0.0.1``
are accepted. This prevents the API key from being sent in the clear.

Attributes:
    ApiSettings: Base URL, key, default model and timeout for the Jev API.
    LogSettings: Log format, level and redaction configuration.
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
    - [judgevet.adapters.outbound.http][]: Takes the values, never the environment.
    - [judgevet.adapters.inbound.cli][]: Reads it once per process.
    - [judgevet.adapters.inbound.logs][]: Configures structured logging.
"""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from judgevet.adapters.inbound.credentials import resolve_key
from judgevet.adapters.inbound.logs import LogSettings as LogsLogSettings
from judgevet.adapters.outbound.network import NetworkConfig
from judgevet.adapters.outbound.retries import RetryPolicy

DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-latest"


class ApiSettings(BaseSettings):
    """Credential sources and connection settings for the Jev API.

    Attributes:
        base_url (str): Root of the Jev API. Defaults to the documented host.
            Must use ``https://`` or loopback ``http://localhost`` or
            ``http://127.0.0.1``. Remote HTTP is rejected to prevent the API
            key from being sent in the clear.
        key (SecretStr | None): The API key. ``None`` until one is supplied,
            which is why every call path reports a missing key rather than
            assuming one.
        key_file (str | None): Optional mounted credential file.
        key_command_timeout (float): Finite positive command deadline in seconds.
        has_key_source (bool): Source presence without IO.
        default_model (str): Model id sent when a call names none.
        max_attempts (int): Total requests per call, including the first.
        retry_base_delay (float): Initial delay ceiling in seconds.
        retry_max_delay (float): Maximum delay ceiling in seconds.
        retry_transport (bool): Permit retries of transport errors.
        retry_policy (RetryPolicy): Validated policy passed to the adapter.
        proxy (SecretStr | None): Explicit proxy URL; masks optional credentials.
        ca_bundle (str | None): Explicit PEM trust bundle path.
        verify (bool): Enable certificate and hostname verification.
        network_config (NetworkConfig): Network configuration for the adapter.
        timeout_seconds (float): Read timeout in seconds. Defaults to 30.0.
            Can be set via ``JEV_API__TIMEOUT_SECONDS`` environment variable.

    Examples:
        ```python
        api = ApiSettings()
        assert api.base_url == "https://api.typesafe.ai"
        ```

    See Also:
        - [judgevet.adapters.inbound.settings.Settings][]: Nests this model.
    """

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    base_url: str = Field(
        default=DEFAULT_BASE_URL,
        validation_alias=AliasChoices("base_url", "TYPESAFE_BASE_URL"),
    )

    @field_validator("base_url", mode="after")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        """Validate that base_url uses HTTPS or is a loopback HTTP URL.

        Args:
            value: The base URL to validate.

        Returns:
            The validated URL.

        Raises:
            ValueError: If the URL uses HTTP but is not loopback (localhost or 127.0.0.1).
        """
        parsed = urlparse(value)
        scheme = parsed.scheme.lower()

        if scheme == "https":
            return value

        if scheme == "http":
            hostname = parsed.hostname or ""
            if hostname in ("localhost", "127.0.0.1"):
                return value
            raise ValueError(
                f"base_url must use https://. The variable JEV_API__BASE_URL "
                f"received a plaintext HTTP URL ({value}). This would send the "
                f"API key in the clear. Use https:// or http://localhost for local testing."
            )

        raise ValueError(
            f"base_url must use https:// or http://. The variable JEV_API__BASE_URL "
            f"received an unsupported scheme in ({value})."
        )

    key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("key", "TYPESAFE_API_KEY"),
    )
    key_file: str | None = None
    key_command_timeout: float = Field(default=5.0, gt=0, allow_inf_nan=False)

    @property
    def has_key_source(self) -> bool:
        """Check source presence without reading files or executing commands.

        Returns:
            Whether a nonempty key/command or a file path is configured.
        """
        return bool(self.key) or self.key_file is not None

    def resolve_key(self, explicit: str | None = None) -> SecretStr | None:
        """Resolve the selected credential source only when requested.

        Args:
            explicit: Optional literal override, which wins over configured sources.

        Returns:
            Wrapped key or None when no source is configured.

        Raises:
            ValueError: If the selected file or command source fails.
        """
        return resolve_key(self.key, self.key_file, self.key_command_timeout, explicit)

    default_model: str = Field(default=DEFAULT_MODEL)

    proxy: SecretStr | None = None
    ca_bundle: str | None = None
    verify: bool = True

    @property
    def network_config(self) -> NetworkConfig:
        """Pass explicit proxy and TLS values to the outbound adapter.

        Returns:
            Immutable network options with proxy credentials omitted from repr.

        Raises:
            ValueError: If CA configuration conflicts with disabled verification.
        """
        return NetworkConfig(
            proxy=self.proxy.get_secret_value() if self.proxy is not None else None,
            ca_bundle=self.ca_bundle,
            verify=self.verify,
        )

    max_attempts: int = Field(default=1, ge=1)

    @field_validator("max_attempts", mode="before")
    @classmethod
    def _validate_max_attempts(cls, value: object) -> object:
        """Reject booleans before numeric settings validation.

        Args:
            value: Explicit or environment-supplied attempt count.

        Returns:
            Input for normal integer validation.

        Raises:
            ValueError: If an explicit boolean is supplied.
        """
        if value is True or value is False:
            raise ValueError("max_attempts must be a positive integer")
        return value

    retry_base_delay: float = Field(default=0.5, ge=0, allow_inf_nan=False)
    retry_max_delay: float = Field(default=5.0, ge=0, allow_inf_nan=False)
    retry_transport: bool = False

    @property
    def retry_policy(self) -> RetryPolicy:
        """Build the shared retry policy from validated settings.

        Returns:
            Immutable policy consumed by the composition roots.
        """
        return RetryPolicy(
            self.max_attempts,
            self.retry_base_delay,
            self.retry_max_delay,
            self.retry_transport,
        )

    timeout_seconds: float = Field(default=30.0)

    @field_validator("timeout_seconds", mode="after")
    @classmethod
    def _validate_timeout_seconds(cls, value: float) -> float:
        """Validate that timeout_seconds is positive.

        Args:
            value: The timeout value in seconds.

        Returns:
            The validated timeout value.

        Raises:
            ValueError: If the value is zero or negative.
        """
        if value <= 0:
            raise ValueError(
                f"timeout_seconds must be positive. The variable JEV_API__TIMEOUT_SECONDS "
                f"received {value}."
            )
        return value


class Settings(BaseSettings):
    """Every setting this client reads, nested per adapter.

    Attributes:
        api (ApiSettings): Base URL, key, default model and timeout for the Jev API.
        log (LogSettings): Log format, level and redaction configuration.

    Examples:
        ```python
        settings = Settings()
        print(settings.api.base_url)
        ```

    See Also:
        - [judgevet.adapters.inbound.settings.ApiSettings][]: The nested model.
        - [judgevet.adapters.inbound.logs.LogSettings][]: Log configuration.
    """

    model_config = SettingsConfigDict(
        env_prefix="JEV_",
        env_nested_delimiter="__",
        extra="ignore",
        frozen=True,
    )

    api: ApiSettings = Field(default_factory=ApiSettings)
    log: LogsLogSettings = Field(default_factory=LogsLogSettings)
