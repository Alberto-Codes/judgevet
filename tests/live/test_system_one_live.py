"""Live tests that call the real Jev System One API.

These tests require a valid TYPESAFE_API_KEY in the environment.
When the key is absent, tests are skipped with a clear message.

Examples:
    ```bash
    # Run all tests except live
    pytest

    # Run live tests only
    pytest -m live

    # Run with a specific key
    TYPESAFE_API_KEY="your-key" pytest -m live
    ```

See Also:
    - [jev_client.adapters.inbound.settings][]: Settings for configuration
    - [jev_client.adapters.outbound.http][]: HTTP adapter
    - [jev_client.domain.questions][]: Question types
    - [jev_client.domain.answers][]: Answer types
"""

from __future__ import annotations

from typing import Any

import pytest

from jev_client.adapters.inbound.settings import Settings
from jev_client.adapters.outbound.http import HTTPSystemOneAdapter
from jev_client.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer


def _parse_raw_answers(raw_answers: dict[str, dict]) -> dict[str, Answer]:
    """Parse raw API answers into domain answer objects.

    Args:
        raw_answers: Raw answer data from the API.

    Returns:
        Dictionary of domain answer objects.

    Raises:
        pytest.fail: If an unknown answer type is encountered.
    """
    answers: dict[str, Answer] = {}
    for name, raw_answer in raw_answers.items():
        answer_type = raw_answer.get("type")
        if answer_type == "noul":
            answers[name] = NoulAnswer(noul=raw_answer["noul"])
        elif answer_type == "choice":
            answers[name] = ChoiceAnswer(
                choice=raw_answer["choice"],
                confidence=raw_answer["confidence"],
                probabilities=raw_answer["probabilities"],
            )
        elif answer_type == "score":
            legend_raw = raw_answer["legend"]
            probabilities_raw = raw_answer["probabilities"]
            legend = {int(k): v for k, v in legend_raw.items()}
            probabilities = {int(k): v for k, v in probabilities_raw.items()}
            answers[name] = ScoreAnswer(
                score=raw_answer["score"],
                confidence=raw_answer["confidence"],
                legend=legend,
                probabilities=probabilities,
            )
        else:
            pytest.fail(f"Unknown answer type in response: {answer_type}")
    return answers


def _assert_usage_structure(usage_data: dict) -> None:
    """Assert usage data has the expected structure.

    Args:
        usage_data: Raw usage data from the API response.
    """
    assert isinstance(usage_data, dict)
    assert "input_tokens" in usage_data or "output_tokens" in usage_data


def _assert_answer_constraints(answers: dict[str, Answer]) -> None:
    """Assert that parsed answers meet domain constraints.

    Args:
        answers: Dictionary of parsed answer objects.
    """
    assert "noul_q" in answers
    assert "choice_q" in answers
    assert "score_q" in answers

    noul_answer = answers["noul_q"]
    assert isinstance(noul_answer, NoulAnswer)
    assert 0.0 <= noul_answer.noul <= 1.0

    choice_answer = answers["choice_q"]
    assert isinstance(choice_answer, ChoiceAnswer)
    assert 0.0 <= choice_answer.confidence <= 1.0
    assert choice_answer.choice in choice_answer.probabilities
    assert all(0.0 <= p <= 1.0 for p in choice_answer.probabilities.values())

    score_answer = answers["score_q"]
    assert isinstance(score_answer, ScoreAnswer)
    assert 0.0 <= score_answer.confidence <= 1.0
    assert len(score_answer.legend) >= 2
    assert len(score_answer.legend) == len(score_answer.probabilities)
    assert all(isinstance(k, int) for k in score_answer.legend)
    assert all(isinstance(k, int) for k in score_answer.probabilities)
    assert all(0.0 <= p <= 1.0 for p in score_answer.probabilities.values())


def _make_live_request(
    api_key: str, base_url: str, model: str, state: str, questions: dict[str, Any]
) -> dict:
    """Make a live API request and return the raw response.

    Args:
        api_key: TypeSafe API key.
        base_url: API base URL.
        model: Model name to use.
        state: State to evaluate.
        questions: Questions to ask.

    Returns:
        Raw API response dictionary.
    """
    adapter = HTTPSystemOneAdapter(
        api_key=api_key,
        base_url=base_url,
        default_model=model,
    )

    try:
        return adapter.system_one(
            state=state,
            questions=questions,
            model=model,
        )
    finally:
        adapter.close()


@pytest.mark.live
def test_system_one_live_with_all_question_types() -> None:
    """Test live API with Noul, Choice, and Score questions.

    Calls real Jev API with one question of each type, verifies response parses
    into expected domain types. Requires TYPESAFE_API_KEY in environment.
    Skips if absent.

    Raises:
        JevAuthError: If the API key is invalid or missing.
        JevServiceError: If the API returns 5xx or a transport error occurs.
        JevResponseError: If the response body cannot be parsed into domain types.
    """
    settings = Settings()
    key = settings.api.key

    if key is None:
        pytest.skip("Missing TYPESAFE_API_KEY environment variable")

    questions = {
        "noul_q": {
            "type": "noul",
            "instructions": "Is 2+2 equal to 4?",
            "criteria": {"yes": "Correct", "no": "Incorrect"},
        },
        "choice_q": {
            "type": "choice",
            "instructions": "Which animal is a cat?",
            "criteria": {"cat": "Feline", "dog": "Canine", "bird": "Feathered"},
        },
        "score_q": {
            "type": "score",
            "instructions": "Rate quality:",
            "criteria": ["Poor", "Fair", "Good", "Excellent"],
        },
    }

    raw_response = _make_live_request(
        api_key=key.get_secret_value(),
        base_url=settings.api.base_url,
        model=settings.api.default_model,
        state="Test content.",
        questions=questions,
    )

    assert "model" in raw_response
    assert "answers" in raw_response
    assert "usage" in raw_response
    _assert_usage_structure(raw_response["usage"])

    answers = _parse_raw_answers(raw_response["answers"])
    _assert_answer_constraints(answers)
