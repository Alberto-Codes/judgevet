"""Prepare opt-in redacted state immediately before request serialization.

Redaction sees a deep copy of ordinary JSON state. The immutable serialized body
is reused across retries. The unconfigured path retains HTTPX JSON handling.
Wire payload fields follow https://docs.typesafe.ai/api.

Examples:
    ```python
    from judgevet.adapters.outbound.request_body import prepare_body

    payload = {"state": "synthetic", "questions": {}, "model": "jev-latest"}
    assert prepare_body(payload, None) is payload
    ```

See Also:
    - [judgevet.ports.StateRedactor][]: Caller-owned transformation protocol.
    - [judgevet.adapters.outbound.http][]: Shared preparation before retries.
    - [judgevet.adapters.outbound.gateway][]: Independent metadata configuration.
"""

import json
from copy import deepcopy
from typing import Any

from judgevet.adapters.outbound.gateway import GatewayOptions
from judgevet.ports import StateRedactor


class AdapterOptions(GatewayOptions, total=False):
    """Extend typed constructor options without changing existing parameters.

    Attributes:
        redactor (StateRedactor | None): Caller-owned synchronous state transformation.

    Examples:
        ```python
        options: AdapterOptions = {"redactor": None}
        assert configured_redactor(options) is None
        ```
    """

    redactor: StateRedactor | None


def configured_redactor(options: AdapterOptions) -> StateRedactor | None:
    """Validate constructor extensions and select explicit redaction.

    Args:
        options: Typed gateway and redactor keywords from an HTTP constructor.

    Returns:
        The optional callback; None leaves the existing path unchanged.

    Raises:
        TypeError: If an untyped caller supplies an unknown keyword.
    """
    if options.keys() - {"gateway", "redactor"}:
        raise TypeError("Unknown HTTP adapter option")
    return options.get("redactor")


def prepare_body(
    payload: dict[str, Any], redactor: StateRedactor | None
) -> dict[str, Any] | bytes:
    """Transform a copied state and snapshot bytes before entering retry handling.

    Args:
        payload: Built state, questions and model fields.
        redactor: Optional trusted caller transformation.

    Returns:
        Existing JSON payload when unconfigured, otherwise immutable UTF-8 bytes.

    Raises:
        TypeError: If transformed state has an unsupported root or is not JSON data.
        ValueError: If transformed data cannot be encoded as finite JSON.
        Exception: If copying state or the caller's transformation fails.
    """
    if redactor is None:
        return payload
    state = redactor.redact(deepcopy(payload["state"]))
    if not isinstance(state, (str, dict, list)):
        raise TypeError("State redactor must return a string, dictionary or list")
    transformed = payload | {"state": state}
    return json.dumps(
        transformed, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
