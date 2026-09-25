"""Prepare question wire forms and opt-in redacted state before serialization.

Redaction sees a deep copy of ordinary JSON state. The immutable serialized body
is reused across retries. The unconfigured path retains HTTPX JSON handling.
The options also carry the caller-held key for the audit record's fingerprint.
Wire payload fields follow https://docs.typesafe.ai/api.

Examples:
    ```python
    from judgevet.adapters.outbound.request_body import prepare_body

    payload = {"state": "synthetic", "questions": {}, "model": "jev-latest"}
    assert prepare_body(payload, None) is payload
    ```

See Also:
    - [judgevet.ports.StateRedactor][]: Caller-owned transformation protocol.
    - [judgevet.ports.AuditSink][]: Optional caller-owned audit destination.
    - [judgevet.domain.spend.SpendCap][]: Optional shared spend cap.
    - [judgevet.adapters.outbound.http][]: Shared preparation before retries.
    - [judgevet.adapters.outbound.gateway][]: Independent metadata configuration.
"""

import json
from copy import deepcopy
from typing import Any

from judgevet._fingerprint import state_fingerprint
from judgevet.adapters.outbound.gateway import GatewayOptions
from judgevet.domain.questions import Choice, Noul, Score
from judgevet.domain.spend import SpendCap
from judgevet.ports import AuditSink, StateRedactor


class AdapterOptions(GatewayOptions, total=False):
    """Extend typed constructor options without changing existing parameters.

    Attributes:
        redactor (StateRedactor | None): Caller-owned synchronous state transformation.
        spend_cap (SpendCap | None): Shared attempt and input-token cap.
        audit (AuditSink | None): Caller-owned destination for one record per call.
        fingerprint_key (bytes | None): Caller-held key for the record's
            `state_fingerprint`. It is never stored on a record or logged.

    Examples:
        ```python
        options: AdapterOptions = {"redactor": None}
        assert configured_redactor(options) is None
        ```
    """

    redactor: StateRedactor | None
    spend_cap: SpendCap | None
    audit: AuditSink | None
    fingerprint_key: bytes | None


def configured_redactor(options: AdapterOptions) -> StateRedactor | None:
    """Validate constructor extensions and select explicit redaction.

    Args:
        options: Typed gateway, redactor, spend cap, audit and fingerprint key
            keywords from an HTTP constructor.

    Returns:
        The optional callback; None leaves the existing path unchanged.

    Raises:
        TypeError: If an untyped caller supplies an unknown keyword.
    """
    known = {"gateway", "redactor", "spend_cap", "audit", "fingerprint_key"}
    if options.keys() - known:
        raise TypeError("Unknown HTTP adapter option")
    return options.get("redactor")


def keyed_fingerprint(key: bytes | None, state: object) -> str | None:
    """Fingerprint the caller's state under a configured key.

    Args:
        key: Caller-held key, or None when fingerprinting is off.
        state: The caller's state, before any redaction.

    Returns:
        The 64-character hex fingerprint, or None when no key is configured.

    Raises:
        TypeError: If the state is not JSON data.
        ValueError: If the state holds a non-finite number.
    """
    return None if key is None else state_fingerprint(key, state)


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


def wire_question(question: Any) -> Any:
    """Convert a Question object to its wire dict format.

    The wire format is:
        - noul:   {"type": "noul",   "instructions": ..., "criteria": {...} or None}
        - choice: {"type": "choice", "instructions": ..., "criteria": {...} or None}
        - score:  {"type": "score",  "instructions": ..., "criteria": [...]  or None}

    A key whose value is None is omitted from the output.

    Args:
        question: A Question object or a raw dict. Non-Question values pass through.

    Returns:
        A wire dict for Question objects, or the original value otherwise.
    """
    if isinstance(question, Noul):
        result: dict[str, Any] = {"type": "noul"}
        if question.instructions is not None:
            result["instructions"] = question.instructions
        if question.criteria is not None:
            result["criteria"] = question.criteria
        return result
    elif isinstance(question, Choice):
        result = {"type": "choice"}
        if question.instructions is not None:
            result["instructions"] = question.instructions
        if question.criteria is not None:
            result["criteria"] = question.criteria
        return result
    elif isinstance(question, Score):
        result = {"type": "score"}
        if question.instructions is not None:
            result["instructions"] = question.instructions
        if question.criteria is not None:
            result["criteria"] = question.criteria
        return result
    # Non-Question values pass through untouched
    return question
