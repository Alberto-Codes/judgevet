"""Validate bounded explicit HTTP fields without including values in errors.

Names follow RFC 9110 sections 5.1 and 5.6.2. Values use a stricter local ASCII
subset than section 5.5. Limits below are judgevet policy, not vendor limits.
See https://www.rfc-editor.org/rfc/rfc9110.html#section-5.

Examples:
    ```python
    from judgevet.adapters.outbound.gateway_headers import snapshot_headers

    assert snapshot_headers({"Example-Tenant": "synthetic"}) == {
        "example-tenant": "synthetic"
    }
    ```

See Also:
    - [judgevet.adapters.outbound.gateway][]: Public gateway configuration.
"""

import re
from collections.abc import Mapping
from types import MappingProxyType

TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
PROTECTED = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "host",
        "content-type",
        "content-length",
        "content-encoding",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "te",
        "trailer",
        "upgrade",
        "expect",
        "cookie",
        "set-cookie",
    }
)
TRACE_FIELDS = frozenset({"traceparent", "tracestate", "baggage"})
MAX_FIELDS = 32
MAX_NAME = 128
MAX_VALUE = 2048
MAX_TOTAL = 8192
ASCII_SPACE = 32
ASCII_TILDE = 126


def field_name(name: str) -> str:
    """Validate and normalize one field name.

    Args:
        name: Caller-selected HTTP field name.

    Returns:
        Lowercase ASCII token.

    Raises:
        ValueError: If the name violates local syntax or length rules.
    """
    if not isinstance(name, str) or len(name) > MAX_NAME or not TOKEN.fullmatch(name):
        raise ValueError("Invalid gateway header name")
    return name.lower()


def field_value(value: str) -> str:
    """Validate printable ASCII without stripping caller values.

    Args:
        value: Explicit field content or credential.

    Returns:
        Unchanged validated text.

    Raises:
        ValueError: If the value contains unsafe characters or edge spaces.
    """
    if (
        not isinstance(value, str)
        or value != value.strip()
        or any(ord(char) < ASCII_SPACE or ord(char) > ASCII_TILDE for char in value)
    ):
        raise ValueError("Invalid gateway header value")
    return value


def snapshot_headers(headers: Mapping[str, str] | None) -> Mapping[str, str]:
    """Copy, normalize and bound a caller metadata map.

    Args:
        headers: Explicit metadata or None for no fields.

    Returns:
        Immutable validated mapping with values excluded from diagnostics.

    Raises:
        ValueError: If fields are invalid, duplicated, protected or oversized.
    """
    result: dict[str, str] = {}
    if headers is not None:
        for name, value in headers.items():
            normalized = field_name(name)
            if normalized in result or normalized in PROTECTED:
                raise ValueError("Duplicate or protected gateway header")
            field_value(value)
            if len(value) > MAX_VALUE:
                raise ValueError("Gateway metadata exceeds value limit")
            result[normalized] = value
    if (
        len(result) > MAX_FIELDS
        or sum(len(k) + len(v) for k, v in result.items()) > MAX_TOTAL
    ):
        raise ValueError("Gateway metadata exceeds aggregate limits")
    return MappingProxyType(result)
