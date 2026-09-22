"""Check policy JSON against typed questions before network composition.

Examples:
    ```bash
    uv run pytest tests/unit/test_cli_policy_parser.py
    ```

See Also:
    - [judgevet.adapters.inbound.cli_policy][]: Validated policy rules.
"""

import json

import pytest

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_policy import parse_policy
from judgevet.domain.questions import Choice, Noul, Score

pytestmark = pytest.mark.unit
QUESTIONS = {
    "noul": Noul(instructions="True?"),
    "choice": Choice(criteria={"yes": "Yes", "no": "No"}),
    "score": Score(criteria=["Poor", "Fair", "Good", "Excellent"]),
}


def test_all_types_and_confidence() -> None:
    """Parse every accepted predicate shape without inventing nested choice fields."""
    text = json.dumps(
        {
            "rules": [
                {"question": "noul", "pass": {"noul": {"min": 0.4, "max": 0.5}}},
                {
                    "question": "choice",
                    "pass": {"choice": "yes", "confidence": {"min": 0.8}},
                },
                {
                    "question": "score",
                    "pass": {"score": {"min": 1.5}, "confidence": {"min": 0.6}},
                },
            ]
        }
    )
    rules = parse_policy(text, QUESTIONS)
    assert [rule.name for rule in rules] == ["noul", "choice", "score"]
    assert [rule.kind for rule in rules] == ["noul", "choice", "score"]
    assert rules[0].minimum == 0.4
    assert rules[0].maximum == 0.5
    assert rules[1].choice == "yes"
    assert rules[1].min_confidence == 0.8
    assert rules[2].minimum == 1.5
    assert rules[2].maximum is None
    assert rules[2].min_confidence == 0.6


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        "[]",
        '{"rules":[]}',
        '{"rules":[null]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":1e1000}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":NaN}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":true}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":0.8,"max":0.2}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":-0.1}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":0.1,"unknown":0}}}]}',
        '{"rules":[{"question":"noul","pass":{"choice":"yes"}}]}',
        '{"rules":[{"question":"private","pass":{"noul":{"min":0.5}}}]}',
        '{"rules":[{"question":"choice","pass":{"choice":"private"}}]}',
        '{"rules":[{"question":"score","pass":{"score":{"max":4}}}]}',
        '{"rules":[{"question":"noul","pass":{"noul":{"min":0.1,"min":0.2}}}]}',
        '{"rules":[],"rules":[]}',
        '{"private',
    ],
)
def test_invalid_policy(text: str) -> None:
    """Reject invalid schemas with a source-specific, sanitized input error."""
    with pytest.raises(InputFailure) as caught:
        parse_policy(text, QUESTIONS)
    assert caught.value.code == 1
    assert "--policy" in str(caught.value)
    assert "private" not in str(caught.value)
