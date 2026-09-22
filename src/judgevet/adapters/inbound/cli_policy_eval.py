"""Policy evaluation for typed question predicates.

Examples:
    ```python
    from judgevet.adapters.inbound.cli_inputs import InputFailure
    from judgevet.adapters.inbound.cli_policy import parse_policy
    from judgevet.adapters.inbound.cli_policy_eval import evaluate_policy
    from judgevet.domain.answers import NoulAnswer, ChoiceAnswer, ScoreAnswer
    from judgevet.domain.questions import Choice, Noul, Score

    questions = {
        "noul": Noul(instructions="True?"),
        "choice": Choice(criteria={"yes": "Yes"}),
        "score": Score(criteria=["Poor", "Fair"]),
    }
    rules = parse_policy(
        '{"rules":[{"question":"noul","pass":{"noul":{"min":0.42}}}]}', questions
    )
    passed, reports = evaluate_policy(rules, {"noul": NoulAnswer(noul=0.42)})
    assert passed is True
    ```

See Also:
    - [judgevet.adapters.inbound.cli_policy][]: Policy schema.
    - [judgevet.adapters.inbound.cli_inputs.InputFailure][]: Exception raised for invalid answers.
    - [judgevet.domain.answers][]: Typed answer definitions.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.adapters.inbound.cli_policy import Rule
from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer


def _extract_noul_answer(answer: Answer) -> float:
    """Extract noul value from a NoulAnswer.

    Args:
        answer: The answer to extract from.

    Returns:
        The noul value as float.

    Raises:
        InputFailure: If answer is not a NoulAnswer.
    """
    if not isinstance(answer, NoulAnswer):
        raise InputFailure("response: answer type mismatch for noul question", code=1)
    return answer.noul


def _extract_choice_answer(answer: Answer) -> tuple[str, float]:
    """Extract choice and confidence from a ChoiceAnswer.

    Args:
        answer: The answer to extract from.

    Returns:
        Tuple of (choice, confidence) values.

    Raises:
        InputFailure: If answer is not a ChoiceAnswer.
    """
    if not isinstance(answer, ChoiceAnswer):
        raise InputFailure("response: answer type mismatch for choice question", code=1)
    return answer.choice, answer.confidence


def _extract_score_answer(answer: Answer) -> tuple[float, float]:
    """Extract score and confidence from a ScoreAnswer.

    Args:
        answer: The answer to extract from.

    Returns:
        Tuple of (score, confidence) values.

    Raises:
        InputFailure: If answer is not a ScoreAnswer.
    """
    if not isinstance(answer, ScoreAnswer):
        raise InputFailure("response: answer type mismatch for score question", code=1)
    return answer.score, answer.confidence


def _is_valid_noul_value(value: float) -> bool:
    """Check if a noul value is valid (finite and in [0,1]).

    Args:
        value: The value to check.

    Returns:
        True if value is finite and in [0,1].
    """
    if not math.isfinite(value):
        return False
    return 0.0 <= value <= 1.0


def _build_report(rule: Rule, passed: bool, detail: str) -> dict[str, str | bool]:
    """Build a report dictionary for a rule.

    Args:
        rule: The rule that was evaluated.
        passed: Whether the rule passed.
        detail: The detail string explaining the comparison.

    Returns:
        Report dictionary with question, pass, and detail.
    """
    return {
        "question": rule.name,
        "pass": passed,
        "detail": detail,
    }


def _evaluate_noul(rule: Rule, answer: Answer) -> tuple[bool, str]:
    """Evaluate noul rule against a NoulAnswer.

    Args:
        rule: The policy rule.
        answer: The answer to evaluate.

    Returns:
        Tuple of (passed, detail).

    Raises:
        InputFailure: If answer is not a NoulAnswer or value is nonfinite.
    """
    value = _extract_noul_answer(answer)
    if not _is_valid_noul_value(value):
        raise InputFailure("response: noul value is nonfinite or out of [0,1]", code=1)
    predicate_ok = (rule.minimum is None or value >= rule.minimum) and (
        rule.maximum is None or value <= rule.maximum
    )
    detail = _build_noul_detail(rule, value, predicate_ok)
    return predicate_ok, detail


def _evaluate_choice(rule: Rule, answer: Answer) -> tuple[bool, str]:
    """Evaluate choice rule against a ChoiceAnswer.

    Args:
        rule: The policy rule.
        answer: The answer to evaluate.

    Returns:
        Tuple of (passed, detail).

    Raises:
        InputFailure: If answer is not a ChoiceAnswer or confidence is nonfinite.
    """
    choice, confidence = _extract_choice_answer(answer)
    choice_ok = choice == rule.choice
    if rule.min_confidence is not None:
        if not math.isfinite(confidence):
            raise InputFailure("response: choice confidence is nonfinite", code=1)
        confidence_ok = confidence >= rule.min_confidence
        passed = choice_ok and confidence_ok
        detail = _build_choice_detail(
            rule, choice, confidence, choice_ok, confidence_ok
        )
    else:
        passed = choice_ok
        detail = _build_choice_detail_no_confidence(rule, choice, choice_ok)
    return passed, detail


def _evaluate_score(rule: Rule, answer: Answer) -> tuple[bool, str]:
    """Evaluate score rule against a ScoreAnswer.

    Args:
        rule: The policy rule.
        answer: The answer to evaluate.

    Returns:
        Tuple of (passed, detail).

    Raises:
        InputFailure: If answer is not a ScoreAnswer or score/confidence is nonfinite.
    """
    score, confidence = _extract_score_answer(answer)
    if not math.isfinite(score):
        raise InputFailure("response: score is nonfinite", code=1)
    predicate_ok = (rule.minimum is None or score >= rule.minimum) and (
        rule.maximum is None or score <= rule.maximum
    )
    confidence_ok = True
    if rule.min_confidence is not None:
        if not math.isfinite(confidence):
            raise InputFailure("response: score confidence is nonfinite", code=1)
        confidence_ok = confidence >= rule.min_confidence
    passed = predicate_ok and confidence_ok
    detail = _build_score_detail(rule, score, confidence, predicate_ok, confidence_ok)
    return passed, detail


def evaluate_policy(
    rules: tuple[Rule, ...], answers: Mapping[str, Answer]
) -> tuple[bool, list[dict[str, str | bool]]]:
    """Evaluate policy rules against typed answers.

    Args:
        rules: Tuple of validated policy rules with score bounds.
        answers: Mapping of question names to typed Answer objects.

    Returns:
        Tuple of (overall_passed, list_of_reports). Overall passed is True only if
        all rules pass. Reports are generated for every rule in order.

    Raises:
        InputFailure: If an answer is missing or has the wrong type for its rule.
            Also raised if any numeric value is nonfinite (nan/inf).
    """
    reports: list[dict[str, str | bool]] = []
    all_passed = True

    for rule in rules:
        # Look up answer
        if rule.name not in answers:
            raise InputFailure("response: missing answer for policy question", code=1)

        answer = answers[rule.name]

        # Evaluate based on rule kind
        if rule.kind == "noul":
            passed, detail = _evaluate_noul(rule, answer)
        elif rule.kind == "choice":
            passed, detail = _evaluate_choice(rule, answer)
        elif rule.kind == "score":
            passed, detail = _evaluate_score(rule, answer)
        else:
            raise InputFailure("response: unknown policy rule kind", code=1)

        if not passed:
            all_passed = False

        reports.append(_build_report(rule, passed, detail))

    return all_passed, reports


def _build_noul_detail(rule: Rule, value: float, passed: bool) -> str:
    """Describe the actual probability comparisons.

    Args:
        rule: Validated Noul rule.
        value: Observed probability.
        passed: Whether the comparisons passed.

    Returns:
        Human-readable comparisons and their verdict.
    """
    parts = []
    if rule.minimum is not None:
        parts.append(f"noul {value} >= {rule.minimum}")
    if rule.maximum is not None:
        parts.append(f"noul {value} <= {rule.maximum}")
    detail = " and ".join(parts) if parts else f"noul {value}"
    detail += f" -> {'pass' if passed else 'fail'}"
    return detail


def _build_choice_detail(
    rule: Rule,
    choice: str,
    confidence: float,
    choice_ok: bool,
    confidence_ok: bool,
) -> str:
    """Describe the label and confidence comparisons.

    Args:
        rule: Validated Choice rule.
        choice: Observed choice label.
        confidence: Observed confidence.
        choice_ok: Whether the label matched.
        confidence_ok: Whether confidence met its floor.

    Returns:
        Human-readable comparisons and their verdict.
    """
    choice_part = f"choice '{choice}' == '{rule.choice}'"
    conf_part = f"confidence {confidence} >= {rule.min_confidence}"
    detail = (
        f"{choice_part} and {conf_part} -> "
        f"{'pass' if (choice_ok and confidence_ok) else 'fail'}"
    )
    return detail


def _build_choice_detail_no_confidence(rule: Rule, choice: str, choice_ok: bool) -> str:
    """Describe an exact label comparison without a confidence predicate.

    Args:
        rule: Validated Choice rule.
        choice: Observed label.
        choice_ok: Whether the label matched.

    Returns:
        Human-readable comparisons and their verdict.
    """
    detail = (
        f"choice '{choice}' == '{rule.choice}' -> {'pass' if choice_ok else 'fail'}"
    )
    return detail


def _build_score_detail(
    rule: Rule, score: float, confidence: float, predicate_ok: bool, confidence_ok: bool
) -> str:
    """Describe the original-scale score and optional confidence comparisons.

    Args:
        rule: Validated Score rule.
        score: Observed score.
        confidence: Observed confidence.
        predicate_ok: Whether the score met its bounds.
        confidence_ok: Whether confidence met its floor.

    Returns:
        Human-readable comparisons and their verdict.
    """
    parts = []
    if rule.minimum is not None:
        parts.append(f"score {score} >= {rule.minimum}")
    if rule.maximum is not None:
        parts.append(f"score {score} <= {rule.maximum}")
    detail = " and ".join(parts) if parts else f"score {score}"
    if rule.min_confidence is not None:
        detail += f" and confidence {confidence} >= {rule.min_confidence}"
    detail += f" -> {'pass' if (predicate_ok and confidence_ok) else 'fail'}"
    return detail
