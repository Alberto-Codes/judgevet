"""Configure HTTPX proxy routing and certificate verification explicitly.

HTTPX defaults and environment behavior are documented at
https://www.python-httpx.org/advanced/ssl/ and
https://www.python-httpx.org/environment_variables/.

Examples:
    ```python
    from judgevet.adapters.outbound.network import NetworkConfig

    assert NetworkConfig().verification() is True
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Sync and async HTTP clients.
    - [judgevet.adapters.inbound.settings][]: Environment configuration.
"""

import ssl
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NetworkConfig:
    """Select explicit network options while retaining secure defaults.

    Attributes:
        proxy (str | None): Explicit HTTPX proxy URL, omitted from representation.
        ca_bundle (str | None): PEM trust bundle replacing default CA roots.
        verify (bool): Verify certificate chains and hostnames by default.

    Examples:
        ```python
        network = NetworkConfig(ca_bundle="/etc/company/ca.pem")
        assert network.verify is True
        ```
    """

    proxy: str | None = field(default=None, repr=False)
    ca_bundle: str | None = None
    verify: bool = True

    def __post_init__(self) -> None:
        """Reject contradictory or incorrectly typed verification choices.

        Raises:
            TypeError: If verify is not a boolean.
            ValueError: If a trust bundle accompanies disabled verification.
        """
        if not isinstance(self.verify, bool):
            raise TypeError("verify must be a boolean")
        if self.ca_bundle is not None and not self.verify:
            raise ValueError("ca_bundle requires verify=True")

    def verification(self) -> ssl.SSLContext | bool:
        """Build explicit trust roots or retain HTTPX verification behavior.

        Returns:
            A verifying context for an explicit CA bundle, otherwise verify.

        Raises:
            ValueError: If the configured CA bundle cannot be loaded.
        """
        if self.ca_bundle is None:
            return self.verify
        if not self.ca_bundle:
            raise ValueError("Cannot load CA bundle")
        try:
            return ssl.create_default_context(cafile=self.ca_bundle)
        except (OSError, ssl.SSLError, ValueError):
            raise ValueError("Cannot load CA bundle") from None
