"""Record Choice confidence beside its probabilities for 2, 3 and 4 options.

This module is a probe for issue #193. Each case sends one Choice question
on the same synthetic state and prints one JSON line with the option count,
the selected choice, its confidence, the probabilities and the resolved
model. The supervisor compares those lines with candidate formulas by hand.
The tests assert only the answer shape, never a formula.

Source: https://docs.typesafe.ai/confidence defines confidence for a Choice
answer. Question and answer shapes follow
https://docs.typesafe.ai/primitives/choice.

The default suite deselects these tests. A missing key skips each test before
any adapter exists. The key stays wrapped until the adapter call expression.

Examples:
    ```bash
    direnv exec . uv run pytest -q -s -m live tests/live/test_choice_confidence_live.py
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: HTTP adapter that makes the call.
    - [judgevet.domain.questions][]: The Choice question.
    - [judgevet.domain.answers][]: The ChoiceAnswer fields printed here.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest

from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.questions import Choice

STATE = (
    "Hello, I was billed twice for my March subscription. Both charges of "
    "$12.99 appear on my card statement on the same day. Please refund one."
)
INSTRUCTIONS = "Which category best describes this support ticket?"
CRITERIA_BY_COUNT: dict[int, dict[str, str]] = {
    2: {
        "billing": "A problem with a charge, invoice or refund",
        "technical": "A problem with the product not working",
    },
    3: {
        "billing": "A problem with a charge, invoice or refund",
        "technical": "A problem with the product not working",
        "account": "A problem with login, profile or account settings",
    },
    4: {
        "billing": "A problem with a charge, invoice or refund",
        "technical": "A problem with the product not working",
        "account": "A problem with login, profile or account settings",
        "fraud": "A charge the customer did not authorise",
    },
}


@pytest.fixture
def live_adapter() -> Iterator[HTTPSystemOneAdapter]:
    """Yield one live adapter and close it after the test.

    Yields:
        An adapter configured from the environment.

    Raises:
        pytest.skip.Exception: If no API key is configured.
    """
    settings = Settings()
    if settings.api.key is None:
        pytest.skip("Missing JEV_API__KEY or TYPESAFE_API_KEY")
    with HTTPSystemOneAdapter(
        api_key=settings.api.key.get_secret_value(),
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
    ) as adapter:
        yield adapter


@pytest.mark.live
@pytest.mark.parametrize("options", [2, 3, 4])
def test_choice_confidence_probe(
    live_adapter: HTTPSystemOneAdapter, options: int
) -> None:
    """Send one Choice question and print confidence beside probabilities.

    Args:
        live_adapter: The live adapter from the fixture.
        options: The number of criteria in the Choice question.

    Raises:
        AssertionError: If the answer shape breaks the probe's checks.
    """
    criteria = CRITERIA_BY_COUNT[options]
    response = live_adapter.system_one(
        state=STATE,
        questions={"choice": Choice(criteria=criteria, instructions=INSTRUCTIONS)},
    )
    answer = response.choices["choice"]
    print(
        json.dumps(
            {
                "probe": "choice_confidence",
                "options": options,
                "choice": answer.choice,
                "confidence": answer.confidence,
                "probabilities": dict(answer.probabilities),
                "resolved_model": response.model,
            }
        )
    )
    assert 0.0 <= answer.confidence <= 1.0
    assert set(answer.probabilities) == set(criteria)
    assert abs(sum(answer.probabilities.values()) - 1) <= 0.02
