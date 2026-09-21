"""Live tests that call the real Jev System One API.

These tests require a valid TYPESAFE_API_KEY in the environment.
When the key is absent, tests are skipped with a clear message.

Handling the key:
    A secret stays wrapped (SecretStr) until the moment it is used. The unwrap
    happens inside the call expression, never in a binding. A binding puts the
    plaintext in a frame local, and pytest prints frame locals of every frame in a
    failing traceback — to the terminal, to CI logs, and to any transcript
    capturing the output. The conftest guard in `tests/conftest.py` redacts the
    configured key from report output as a backstop; it cannot reach `-s`/`--capture=no`
    output, so the rule is the primary defence. Note that the guard is necessary
    here because `--showlocals` is in `addopts`, so pytest prints every frame
    local, not just arguments.

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
    - [judgevet.adapters.inbound.settings][]: Settings for configuration
    - [judgevet.adapters.outbound.http][]: HTTP adapter
    - [judgevet.domain.questions][]: Question types
    - [judgevet.domain.answers][]: Answer types
"""

from __future__ import annotations

from typing import Any

import pytest

from judgevet.adapters.inbound.settings import Settings
from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
from judgevet.domain.questions import Choice, Noul
from judgevet.domain.response import SystemOneResponse


def _assert_usage_structure(usage: Any) -> None:
    """Assert usage data has the expected structure.

    Args:
        usage: Usage object or dict from the API response.
    """
    if isinstance(usage, dict):
        assert "input_tokens" in usage or "output_tokens" in usage
    else:
        # SystemOneResponse
        assert usage.input_tokens is not None or usage.output_tokens is not None


def _assert_answer_constraints(answers: dict[str, Any]) -> None:
    """Assert that parsed answers meet domain constraints.

    Args:
        answers: Dictionary of parsed answer objects.
    """
    assert "noul_q" in answers
    assert "choice_q" in answers
    assert "score_q" in answers

    noul_answer = answers["noul_q"]
    assert 0.0 <= noul_answer.noul <= 1.0

    choice_answer = answers["choice_q"]
    assert 0.0 <= choice_answer.confidence <= 1.0
    assert choice_answer.choice in choice_answer.probabilities
    assert all(0.0 <= p <= 1.0 for p in choice_answer.probabilities.values())

    score_answer = answers["score_q"]
    assert 0.0 <= score_answer.confidence <= 1.0
    assert len(score_answer.legend) >= 2
    assert len(score_answer.legend) == len(score_answer.probabilities)
    assert all(isinstance(k, int) for k in score_answer.legend)
    assert all(isinstance(k, int) for k in score_answer.probabilities)
    assert all(0.0 <= p <= 1.0 for p in score_answer.probabilities.values())


def _assert_score_legend_echoes_criteria(
    score_answer: Any,
    criteria: list[str],
) -> None:
    """Assert that score answer legend exactly echoes the sent criteria.

    The Jev API returns a legend mapping each score level (integer position)
    back to its description string. This is deterministic proof the service
    received and used the criteria list, not discarded it.

    Args:
        score_answer: ScoreAnswer from the API response.
        criteria: The exact list of descriptions sent.
    """
    expected_legend = {i: criteria[i] for i in range(len(criteria))}
    assert score_answer.legend == expected_legend, (
        f"Legend {score_answer.legend} does not match expected {expected_legend}"
    )


def _make_live_request(
    api_key: str, base_url: str, model: str, state: str, questions: dict[str, Any]
) -> SystemOneResponse:
    """Make a live API request and return the typed response.

    Args:
        api_key: TypeSafe API key.
        base_url: API base URL.
        model: Model name to use.
        state: State to evaluate.
        questions: Questions to ask.

    Returns:
        Typed SystemOneResponse.
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


def _live_test_questions() -> dict[str, Any]:
    """Return questions for live tests.

    Returns:
        Dictionary with one question of each type: Noul, Choice, Score.
    """
    return {
        "noul_q": {
            "type": "noul",
            "instructions": "Is 2+2 equal to 4?",
            "criteria": {"true": "Correct", "false": "Incorrect"},
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

    questions = _live_test_questions()

    response = _make_live_request(
        api_key=key.get_secret_value(),
        base_url=settings.api.base_url,
        model=settings.api.default_model,
        state="Test content.",
        questions=questions,
    )

    # jev-latest is an alias that the service resolves to a concrete version.
    # The response returns the resolved version, not the alias.
    # See: https://typesafe.ai/docs/system-one/api/api-parameters#model
    assert response.model.startswith("jev-")
    _assert_answer_constraints(response.answers)
    _assert_usage_structure(response.usage)

    # Verify score legend echoes the sent criteria exactly
    score_answer = response.answers["score_q"]
    _assert_score_legend_echoes_criteria(
        score_answer,
        ["Poor", "Fair", "Good", "Excellent"],
    )


@pytest.mark.live
def test_documented_example_runs() -> None:
    """Test the documented example from the package docstring.

    This test executes the example in the package docstring against the live API.
    It uses a bare Noul without criteria to verify the omission rule.

    The example in question is:
        Noul(instructions="Is this valid?")
    which must serialize to:
        {"type": "noul", "instructions": "Is this valid?"}

    Raises:
        JevAuthError: If the API key is invalid or missing.
        JevServiceError: If the API returns 5xx or a transport error occurs.
        JevResponseError: If the response body cannot be parsed.
    """
    settings = Settings()
    key = settings.api.key

    if key is None:
        pytest.skip("Missing TYPESAFE_API_KEY environment variable")

    adapter = HTTPSystemOneAdapter(
        api_key=key.get_secret_value(),
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
    )

    try:
        # This is the example from the package docstring: bare Noul without criteria
        response: SystemOneResponse = adapter.system_one(
            state="Test content for documented example.",
            questions={
                "bare_noul": Noul(instructions="Is this valid?"),
                "choice": Choice(
                    criteria={"a": "Option A", "b": "Option B"},
                    instructions="Choose one:",
                ),
            },
        )

        # Just verify it ran and parsed
        assert response.model.startswith("jev-")
        assert "bare_noul" in response.answers
        assert "choice" in response.answers
    finally:
        adapter.close()


def _run_noul_baseline_call(
    adapter: HTTPSystemOneAdapter,
) -> float:
    """Run baseline noul call without criteria.

    Args:
        adapter: HTTPSystemOneAdapter instance.

    Returns:
        The noul probability from the response.
    """
    response = adapter.system_one(
        state="I emailed you last week about this and nobody replied.",
        questions={
            "noul": {
                "type": "noul",
                "instructions": "Has the customer contacted us before?",
            },
        },
        model="jev-latest",
    )
    noul_answer = response.answers["noul"]
    # ty can't narrow the union type from dict lookup, so use ty: ignore
    return noul_answer.noul  # ty: ignore


def _run_noul_inverted_call(
    adapter: HTTPSystemOneAdapter,
) -> float:
    """Run noul call with inverted criteria.

    Args:
        adapter: HTTPSystemOneAdapter instance.

    Returns:
        The noul probability from the response.
    """
    response = adapter.system_one(
        state="I emailed you last week about this and nobody replied.",
        questions={
            "noul": {
                "type": "noul",
                "instructions": "Has the customer contacted us before?",
                "criteria": {
                    "true": "No prior contact of any kind is mentioned",
                    "false": "The state mentions a prior email, attempt, or reply",
                },
            },
        },
        model="jev-latest",
    )
    noul_answer = response.answers["noul"]
    # ty can't narrow the union type from dict lookup, so use ty: ignore
    return noul_answer.noul  # ty: ignore


@pytest.mark.live
def test_noul_criteria_differential() -> None:
    """Test that noul criteria keys `true`/`false` are read by the service.

    Measures the differential between two calls:
    - call A: no criteria (baseline)
    - call B: explicit criteria with `true`/`false` keys (inverted)

    The measured effect in issue #105 was 0.13 and 0.17, so asserting a
    minimum gap of 0.10 is defensible: well above noise floor (~0.02) but
    below smallest observed effect (0.13).

    Directional assertion: `n_base - n_inv >= 0.10`. Exact values are not
    asserted because the same baseline call measured 0.93 and 0.95 across
    two runs — the model is a judgment model, not a switch.

    Two live calls are made. `@pytest.mark.live`, excluded from the default run.

    Raises:
        JevAuthError: If the API key is invalid or missing.
        JevServiceError: If the API returns 5xx or a transport error occurs.
        JevResponseError: If the response body cannot be parsed.
    """
    settings = Settings()
    key = settings.api.key

    if key is None:
        pytest.skip("Missing TYPESAFE_API_KEY environment variable")

    adapter = HTTPSystemOneAdapter(
        api_key=key.get_secret_value(),
        base_url=settings.api.base_url,
        default_model=settings.api.default_model,
    )

    try:
        n_base = _run_noul_baseline_call(adapter)
        n_inv = _run_noul_inverted_call(adapter)
        gap = n_base - n_inv
        assert gap >= 0.10, (
            f"Gap {gap:.4f} < 0.10. "
            f"Baseline: {n_base:.4f}, Inverted: {n_inv:.4f}. "
            f"Expected baseline > inverted by at least 0.10."
        )
    finally:
        adapter.close()
