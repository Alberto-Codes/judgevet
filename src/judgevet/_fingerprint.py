"""Compute the keyed state fingerprint outside the pure domain.

The fingerprint is HMAC-SHA-256 under a caller-held key over a fixed label, a
zero byte and the state as compact sorted-key JSON. The label and zero byte
follow the `Label || 0x00 || Context` input of NIST SP 800-108.
Source: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-108r1-upd1.pdf.
A keyed hash is only as irreversible as the key is secret, and equal inputs
still give equal outputs.
Source: https://arxiv.org/pdf/1802.07975.

Examples:
    ```python
    from judgevet._fingerprint import state_fingerprint

    value = state_fingerprint(bytes(32), "synthetic")
    assert value.startswith("ddc817f8d4f77bdd")
    assert len(value) == 64
    ```

See Also:
    - [judgevet.domain.audit.JudgmentRecord][]: Carries the fingerprint.
    - [judgevet.adapters.outbound.http][]: Computes it per logical call.
    - [judgevet.testing][]: The fakes compute it the same way.
"""

from __future__ import annotations

import hashlib
import hmac
import json

_LABEL = b"judgevet-state-v1\x00"


def state_fingerprint(key: bytes, state: object) -> str:
    """Return the lowercase hex HMAC-SHA-256 of the labelled state bytes.

    Args:
        key: Caller-held secret key. It is never stored or logged.
        state: The caller's state, before any redaction.

    Returns:
        A 64-character lowercase hex digest.

    Raises:
        TypeError: If the state is not JSON data.
        ValueError: If the state holds a non-finite number.
    """
    text = json.dumps(
        state,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hmac.new(key, _LABEL + text.encode("utf-8"), hashlib.sha256).hexdigest()
