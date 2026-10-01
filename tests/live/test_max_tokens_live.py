"""Live probes of the two Jev max-tokens budgets (#192).

The vendor states two budgets for `jev-1.13.0`: 64k tokens per request, and
32k tokens for `state` plus the single longest question.
Source: https://docs.typesafe.ai/models.md. One earlier call sent a
400,000-character state and got status 400 with the body
`{"detail": {"error_type": "max_tokens_exceeded"}}`.
Source: https://github.com/Alberto-Codes/judgevet/issues/39#issuecomment-5825759575.

The tokenizer is unknown. Sizes here use the estimate of four characters per
token, so 400,000 characters is about 100k tokens, above both budgets, and
180,000 characters is about 45k tokens, between them. The estimate is not a
measurement.

Each state is generated in code from varied English words, not one repeated
character, which a tokenizer may compress. No state is read from a file, and
no state contains the API key.

Each test prints one JSON line with the character count, the outcome, the
status and the resolved model. Run with `-s` to see the lines. The module
makes two paid calls; the adapter retries nothing.

Handling the key:
    The fixture reads the key from `JEV_API__KEY` or `TYPESAFE_API_KEY`
    through `Settings`, keeps it wrapped, and unwraps it inside the adapter
    call expression. No test binds the plaintext key to a local.

Examples:
    ```bash
    TYPESAFE_API_KEY="your-key" pytest -m live -s tests/live/test_max_tokens_live.py
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: HTTP adapter that maps the 400 body
    - [judgevet.domain.errors][]: `JevMaxTokensExceededError`
    - [judgevet.domain.response][]: `SystemOneResponse`
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.adapters.outbound.retries import RetryPolicy
from judgevet.domain.errors import JevMaxTokensExceededError
from judgevet.domain.response import SystemOneResponse

OVERSIZED_CHARACTERS = 400_000
BETWEEN_BUDGETS_CHARACTERS = 180_000
TIMEOUT_SECONDS = 180.0

_WORDS = (
    "river",
    "mountain",
    "lantern",
    "harvest",
    "copper",
    "meadow",
    "whisper",
    "journey",
    "anchor",
    "orchard",
    "thunder",
    "velvet",
    "compass",
    "granite",
    "harbor",
    "saddle",
    "quarrel",
    "blossom",
    "furnace",
    "ledger",
    "pilgrim",
    "marble",
    "tangent",
    "orbit",
    "falcon",
    "cinder",
    "garden",
    "violin",
    "parcel",
    "summit",
    "beacon",
    "timber",
    "canvas",
    "ribbon",
    "mirror",
    "glacier",
    "pepper",
    "island",
    "lattice",
    "rocket",
    "shadow",
    "willow",
    "engine",
    "fabric",
    "puzzle",
    "kettle",
    "signal",
    "meadowlark",
    "bramble",
    "castle",
    "harvestman",
    "lighthouse",
    "quarry",
)

_QUESTIONS: dict[str, Any] = {
    "noul_q": {
        "type": "noul",
        "instructions": "Does this text mention a river?",
    },
}


def build_state(characters: int) -> str:
    """Build a state of exactly the given length from varied English words.

    The word order follows a fixed arithmetic sequence, so the state is
    deterministic and does not repeat one short pattern.

    Args:
        characters: The exact length of the returned state.

    Returns:
        A string of `characters` characters made of space-separated words.
    """
    parts: list[str] = []
    length = 0
    index = 0
    while length < characters:
        word = _WORDS[(index * 37 + index // len(_WORDS)) % len(_WORDS)]
        parts.append(word)
        length += len(word) + 1
        index += 1
    return " ".join(parts)[:characters]


def _record(
    case: str, characters: int, outcome: str, status: int | None, model: str | None
) -> dict[str, Any]:
    """Print one JSON line for a probe result and return it.

    Args:
        case: The probe case name.
        characters: The length of the state sent.
        outcome: `max_tokens_exceeded` or `answered`.
        status: The HTTP status, or None when the service answered.
        model: The resolved model, or None when the service refused.

    Returns:
        The record that was printed.
    """
    record = {
        "probe": "max_tokens",
        "case": case,
        "characters": characters,
        "outcome": outcome,
        "status": status,
        "resolved_model": model,
    }
    print(json.dumps(record))
    return record


def _send_between_budgets(adapter: HTTPSystemOneAdapter) -> dict[str, Any]:
    """Send the between-budgets state and classify the outcome.

    Args:
        adapter: The live adapter.

    Returns:
        The printed record. Any exception other than
        `JevMaxTokensExceededError` propagates.
    """
    state = build_state(BETWEEN_BUDGETS_CHARACTERS)
    try:
        response = adapter.system_one(state=state, questions=_QUESTIONS)
    except JevMaxTokensExceededError as exc:
        return _record(
            "between_budgets", len(state), "max_tokens_exceeded", exc.status_code, None
        )
    assert isinstance(response, SystemOneResponse)
    return _record("between_budgets", len(state), "answered", 200, response.model)


@pytest.fixture
def live_adapter() -> Iterator[HTTPSystemOneAdapter]:
    """Yield a live adapter with a long timeout and no retries.

    Yields:
        An `HTTPSystemOneAdapter` bound to the configured key.

    Raises:
        pytest.skip.Exception: When no API key is configured.
    """
    settings = Settings()
    key = settings.api.key
    if key is None:
        pytest.skip("Missing JEV_API__KEY or TYPESAFE_API_KEY")
    adapter = HTTPSystemOneAdapter(
        api_key=key.get_secret_value(),
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
        timeout_seconds=TIMEOUT_SECONDS,
        retry=RetryPolicy(max_attempts=1),
    )
    try:
        yield adapter
    finally:
        adapter.close()


@pytest.mark.live
def test_oversized_state_raises_max_tokens(
    live_adapter: HTTPSystemOneAdapter,
) -> None:
    """Send a 400,000-character state and expect the max-tokens error.

    The state is about 100k tokens on the four-characters-per-token estimate,
    above both budgets. The test asserts the error, its status and that it is
    not retryable, then prints one JSON line.

    Args:
        live_adapter: The live adapter fixture.
    """
    state = build_state(OVERSIZED_CHARACTERS)
    with pytest.raises(JevMaxTokensExceededError) as exc_info:
        live_adapter.system_one(state=state, questions=_QUESTIONS)
    assert exc_info.value.retryable is False
    assert exc_info.value.status_code == 400
    _record("oversized", len(state), "max_tokens_exceeded", 400, None)


@pytest.mark.live
def test_state_between_budgets_records_which_fires(
    live_adapter: HTTPSystemOneAdapter,
) -> None:
    """Send a state between the budgets and record which outcome happened.

    The state is about 180,000 characters, about 45k tokens on the
    four-characters-per-token estimate: above the 32k state-plus-question
    budget and below the 64k request budget. The outcome is unknown on
    purpose. `max_tokens_exceeded` means the 32k budget fires alone;
    `answered` means the service did not enforce 32k on this input. Both
    pass. Only a third outcome, any other exception, fails the test.

    Args:
        live_adapter: The live adapter fixture.
    """
    record = _send_between_budgets(live_adapter)
    assert record["outcome"] in {"max_tokens_exceeded", "answered"}
    assert record["characters"] == BETWEEN_BUDGETS_CHARACTERS
