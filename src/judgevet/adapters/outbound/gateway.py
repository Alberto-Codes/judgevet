"""Configure explicit gateway credentials and metadata without implicit forwarding.

Apigee documents configurable key fields at
https://docs.cloud.google.com/apigee/docs/api-platform/reference/policies/verify-api-key-policy.
Direct defaults retain TypeSafe authentication: https://docs.typesafe.ai/api.
Trace fields are caller text, not automatic W3C tracing or baggage collection.
See https://www.w3.org/TR/trace-context/ and https://www.w3.org/TR/baggage/.

Examples:
    ```python
    from judgevet.adapters.outbound.gateway import GatewayConfig, RequestMetadata

    gateway = GatewayConfig(auth_header="x-apikey", auth_scheme="")
    metadata = RequestMetadata(headers={"Example-Tenant": "synthetic"})
    assert gateway.request_headers(metadata)["example-tenant"] == "synthetic"
    ```

See Also:
    - [judgevet.adapters.outbound.gateway_headers][]: Syntax and local limits.
    - [judgevet.adapters.outbound.http][]: Sync and async transport.
    - [judgevet.diagnostics][]: Explicit scoped correlation.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypedDict

from judgevet.adapters.outbound.gateway_headers import (
    PROTECTED,
    TOKEN,
    TRACE_FIELDS,
    field_name,
    field_value,
    snapshot_headers,
)
from judgevet.diagnostics import current_request_id


@dataclass(frozen=True)
class RequestMetadata:
    """Snapshot explicit per-call metadata with case-insensitive field names.

    Attributes:
        headers (Mapping[str, str]): Immutable string fields, omitted from repr.

    Examples:
        ```python
        metadata = RequestMetadata(headers={"Example-Tenant": "synthetic"})
        assert metadata.headers["example-tenant"] == "synthetic"
        ```
    """

    headers: Mapping[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Validate and copy fields before a call can transmit them.

        Raises:
            ValueError: If fields violate the metadata contract.
        """
        object.__setattr__(self, "headers", snapshot_headers(self.headers))


@dataclass(frozen=True)
class GatewayConfig:
    """Select authentication, default metadata and deliberate correlation.

    Custom authentication replaces Authorization; the caller supplies the gateway
    credential through the adapter's existing api_key argument.

    Attributes:
        auth_header (str): Credential field, default Authorization.
        auth_scheme (str): Token prefix, default Bearer; empty sends a bare key.
        headers (Mapping[str, str] | None): Immutable defaults, omitted from repr.
        request_id_header (str | None): Optional field for the scoped request ID.

    Examples:
        ```python
        gateway = GatewayConfig(auth_header="x-apikey", auth_scheme="")
        assert gateway.authentication("dummy")["x-apikey"] == "dummy"
        ```
    """

    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    headers: Mapping[str, str] | None = field(default=None, repr=False)
    request_id_header: str | None = None

    def __post_init__(self) -> None:
        """Validate configuration before the adapter acquires a client.

        Raises:
            ValueError: If names, scheme, fields or correlation conflict.
        """
        auth = field_name(self.auth_header)
        if auth in (PROTECTED - {"authorization"}) | TRACE_FIELDS:
            raise ValueError("Protected gateway authentication header")
        if not isinstance(self.auth_scheme, str) or (
            self.auth_scheme and not TOKEN.fullmatch(self.auth_scheme)
        ):
            raise ValueError("Invalid gateway authentication scheme")
        if self.request_id_header is not None:
            correlation = field_name(self.request_id_header)
            if correlation in PROTECTED | TRACE_FIELDS | {auth}:
                raise ValueError("Protected gateway correlation header")
        object.__setattr__(self, "headers", snapshot_headers(self.headers))
        self.request_headers()

    def authentication(self, key: str) -> dict[str, str]:
        """Build the single credential field and JSON content type.

        Args:
            key: Credential already resolved by the caller.

        Returns:
            Authentication and payload fields for the owned client.

        Raises:
            ValueError: If the credential contains unsafe field content.
        """
        field_value(key)
        value = f"{self.auth_scheme} {key}" if self.auth_scheme else key
        return {self.auth_header: value, "Content-Type": "application/json"}

    def request_headers(
        self, metadata: RequestMetadata | None = None
    ) -> dict[str, str]:
        """Snapshot merged metadata and the opted-in scoped ID for one logical call.

        Args:
            metadata: Per-call fields, which replace defaults case-insensitively.

        Returns:
            Fresh validated request fields reused across retry attempts.

        Raises:
            ValueError: If merged fields conflict or exceed local limits.
        """
        headers = dict(self.headers or {})
        if metadata is not None:
            headers.update(metadata.headers)
        if self.auth_header.lower() in headers:
            raise ValueError("Protected gateway authentication header")
        if self.request_id_header is not None:
            correlation = self.request_id_header.lower()
            if correlation in headers:
                raise ValueError("Gateway correlation header conflicts with metadata")
            request_id = current_request_id()
            if request_id is not None:
                headers[correlation] = request_id
        return dict(snapshot_headers(headers))


class GatewayOptions(TypedDict, total=False):
    """Type the optional adapter extension without changing existing parameters.

    Attributes:
        gateway (GatewayConfig | None): Explicit configuration or direct defaults.
    """

    gateway: GatewayConfig | None


def configured_gateway(options: GatewayOptions) -> GatewayConfig:
    """Resolve typed constructor extensions and reject unknown runtime keywords.

    Args:
        options: Keyword extensions accepted by either HTTP adapter.

    Returns:
        Explicit gateway or the unchanged direct default.

    Raises:
        TypeError: If an untyped caller supplies an unknown option.
    """
    if options.keys() - {"gateway"}:
        raise TypeError("Unknown HTTP adapter option")
    return options.get("gateway") or GatewayConfig()
