"""Policy JSON parser for typed question validation.

Examples:
    ```python
    from judgevet.adapters.inbound.cli_policy import parse_policy
    from judgevet.domain.questions import Noul, Choice, Score

    questions = {
        "noul": Noul(instructions="True?"),
        "choice": Choice(criteria={"yes": "Yes", "no": "No"}),
        "score": Score(criteria=["Poor", "Fair", "Good"]),
    }
    text = '''
    {
        "rules": [
            {"question": "noul", "pass": {"noul": {"min": 0.8}}},
            {"question": "choice", "pass": {"choice": "yes", "confidence": {"min": 0.5}}},
            {"question": "score", "pass": {"score": {"min": 1.0}, "confidence": {"min": 0.6}}}
        ]
    }
    '''
    rules = parse_policy(text, questions)
    assert len(rules) == 3
    ```

See Also:
    - [judgevet.adapters.inbound.cli_inputs.InputFailure][]: Exception raised for invalid policy.
    - [judgevet.domain.questions][]: Typed question definitions.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from judgevet.adapters.inbound.cli_inputs import InputFailure
from judgevet.domain.questions import Choice, Noul, Question, Score


@dataclass(frozen=True)
class Rule:
    """A validated policy rule.

    Attributes:
        name (str): Question name from the policy.
        kind (str): Question type: 'noul', 'choice', or 'score'.
        minimum (float | None): Minimum value for range predicates.
        maximum (float | None): Maximum value for range predicates.
        choice (str | None): Exact choice label for choice predicates.
        min_confidence (float | None): Minimum confidence for Choice/Score predicates.
        score_min (float): Minimum allowed score value (0 for all scores).
        score_max (float): Maximum allowed score value (len(criteria)-1).

    Examples:
        ```python
        rule = Rule("clear", "noul", minimum=0.8)
        assert rule.minimum == 0.8
        ```
    """

    name: str
    kind: str
    minimum: float | None = None
    maximum: float | None = None
    choice: str | None = None
    min_confidence: float | None = None
    score_min: float = 0.0
    score_max: float = 0.0


def _check_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Check for duplicate keys in JSON object pairs.

    Args:
        pairs: Key-value pairs from JSON parsing.

    Returns:
        Pairs as dictionary.

    Raises:
        InputFailure: If duplicate keys are found.
    """
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise InputFailure("--policy: duplicate key in JSON object", code=1)
        seen.add(key)
    return dict(pairs)


def _is_finite_number(value: object) -> bool:
    """Check if value is a finite number (not bool, not inf, not nan).

    Args:
        value: Value to check.

    Returns:
        True if value is a finite number.
    """
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return isinstance(value, int) or math.isfinite(value)


def _validate_range_object(
    obj: dict[str, Any],
    kind: str,
    min_bound: float,
    max_bound: float,
    allow_min: bool = True,
    allow_max: bool = True,
) -> tuple[float | None, float | None]:
    """Validate a range object (min/max) for a predicate.

    Args:
        obj: The range object to validate.
        kind: Predicate kind ('noul', 'score').
        min_bound: Minimum allowed value.
        max_bound: Maximum allowed value.
        allow_min: Whether min is allowed.
        allow_max: Whether max is allowed.

    Returns:
        Tuple of (minimum, maximum) values.

    Raises:
        InputFailure: If validation fails.
    """
    allowed_keys = set()
    if allow_min:
        allowed_keys.add("min")
    if allow_max:
        allowed_keys.add("max")

    # Check for unknown keys
    for key in obj:
        if key not in allowed_keys:
            raise InputFailure(f"--policy: {kind} predicate has unknown field", code=1)

    # Must have at least one bound
    if len(obj) == 0:
        raise InputFailure(
            f"--policy: {kind} predicate requires at least one bound", code=1
        )

    minimum = _parse_bound(obj, "min", kind, min_bound, max_bound)
    maximum = _parse_bound(obj, "max", kind, min_bound, max_bound)

    # min <= max check
    if minimum is not None and maximum is not None and minimum > maximum:
        raise InputFailure(f"--policy: {kind} min cannot exceed max", code=1)

    return minimum, maximum


def _parse_bound(
    obj: dict[str, Any],
    bound_name: str,
    kind: str,
    min_bound: float,
    max_bound: float,
) -> float | None:
    """Parse and validate a single bound value.

    Args:
        obj: The range object.
        bound_name: Name of the bound ('min' or 'max').
        kind: Predicate kind.
        min_bound: Minimum allowed value for this bound.
        max_bound: Maximum allowed value for this bound.

    Returns:
        The bound value as float, or None if not present.

    Raises:
        InputFailure: If validation fails.
    """
    if bound_name not in obj:
        return None

    val = obj[bound_name]
    if not _is_finite_number(val):
        raise InputFailure(
            f"--policy: {kind} {bound_name} must be a finite number", code=1
        )
    if val < min_bound or val > max_bound:
        raise InputFailure(
            f"--policy: {kind} {bound_name} must be in [{min_bound}, {max_bound}]",
            code=1,
        )
    return float(val)


def _parse_noul_predicate(
    obj: dict[str, Any], question: Noul
) -> tuple[float | None, float | None, float | None]:
    """Parse and validate noul predicate.

    Args:
        obj: The pass object containing only the 'noul' range.
        question: The Noul question.

    Returns:
        Tuple of (minimum, maximum, min_confidence) values.

    Raises:
        InputFailure: If validation fails.
    """
    if not isinstance(question, Noul):
        raise InputFailure("--policy: question is not a noul type", code=1)

    # The noul predicate is the value of the 'noul' key
    if "noul" not in obj:
        raise InputFailure("--policy: noul predicate requires 'noul' field", code=1)
    noul_obj = obj["noul"]
    if not isinstance(noul_obj, dict):
        raise InputFailure("--policy: noul range must be an object", code=1)

    # Noul range must be in [0, 1]
    minimum, maximum = _validate_range_object(
        noul_obj, "noul", 0.0, 1.0, allow_min=True, allow_max=True
    )

    return minimum, maximum, None


def _parse_score_predicate(
    obj: dict[str, Any], question: Score
) -> tuple[float | None, float | None, float | None]:
    """Parse and validate score predicate.

    Args:
        obj: The pass object containing 'score' range and optionally 'confidence'.
        question: The Score question.

    Returns:
        Tuple of (minimum, maximum, min_confidence) values.

    Raises:
        InputFailure: If validation fails.
    """
    if not isinstance(question, Score):
        raise InputFailure("--policy: question is not a score type", code=1)

    # The score predicate is the value of the 'score' key
    if "score" not in obj:
        raise InputFailure("--policy: score predicate requires 'score' field", code=1)
    score_obj = obj["score"]
    if not isinstance(score_obj, dict):
        raise InputFailure("--policy: score range must be an object", code=1)

    # Score bounds are [0, len(criteria)-1]
    min_bound = 0.0
    max_bound = float(len(question.criteria) - 1)

    minimum, maximum = _validate_range_object(
        score_obj, "score", min_bound, max_bound, allow_min=True, allow_max=True
    )

    # Parse optional confidence
    min_confidence = None
    if "confidence" in obj:
        conf_obj = obj["confidence"]
        if not isinstance(conf_obj, dict):
            raise InputFailure("--policy: confidence must be an object", code=1)

        # Confidence object must have exactly "min"
        if len(conf_obj) != 1 or "min" not in conf_obj:
            raise InputFailure(
                "--policy: confidence object must have exactly 'min' field", code=1
            )

        min_conf = conf_obj["min"]
        if not _is_finite_number(min_conf):
            raise InputFailure(
                "--policy: confidence min must be a finite number, not bool or nonfinite",
                code=1,
            )
        if min_conf < 0.0 or min_conf > 1.0:
            raise InputFailure("--policy: confidence min must be in [0.0, 1.0]", code=1)
        min_confidence = float(min_conf)

    return minimum, maximum, min_confidence


def _parse_choice_predicate(
    obj: dict[str, Any], question: Choice
) -> tuple[str | None, float | None]:
    """Parse and validate choice predicate.

    Args:
        obj: The pass object containing 'choice' and optionally 'confidence'.
        question: The Choice question.

    Returns:
        Tuple of (choice, min_confidence) values.

    Raises:
        InputFailure: If validation fails.
    """
    if not isinstance(question, Choice):
        raise InputFailure("--policy: question is not a choice type", code=1)

    known_keys = {"choice", "confidence"}
    for key in obj:
        if key not in known_keys:
            raise InputFailure("--policy: choice predicate has unknown field", code=1)

    # Must have choice
    if "choice" not in obj:
        raise InputFailure("--policy: choice predicate requires 'choice' field", code=1)

    choice_val = obj["choice"]
    if not isinstance(choice_val, str):
        raise InputFailure("--policy: choice value must be a string", code=1)

    # Choice must exist in question criteria
    if choice_val not in question.criteria:
        raise InputFailure(
            "--policy: choice value not found in question criteria", code=1
        )

    # Parse optional confidence
    min_confidence = None
    if "confidence" in obj:
        conf_obj = obj["confidence"]
        if not isinstance(conf_obj, dict):
            raise InputFailure("--policy: confidence must be an object", code=1)

        # Confidence object must have exactly "min"
        if len(conf_obj) != 1 or "min" not in conf_obj:
            raise InputFailure(
                "--policy: confidence object must have exactly 'min' field", code=1
            )

        min_conf = conf_obj["min"]
        if not _is_finite_number(min_conf):
            raise InputFailure(
                "--policy: confidence min must be a finite number, not bool or nonfinite",
                code=1,
            )
        if min_conf < 0.0 or min_conf > 1.0:
            raise InputFailure("--policy: confidence min must be in [0.0, 1.0]", code=1)
        min_confidence = float(min_conf)

    return choice_val, min_confidence


def _validate_rule(
    rule: dict[str, Any],
    questions: Mapping[str, Question],
    seen_names: set[str],
) -> Rule:
    """Validate a single rule and return a Rule instance.

    Args:
        rule: The rule object to validate.
        questions: Mapping of question names to Question instances.
        seen_names: Set of already seen rule names (for duplicate detection).

    Returns:
        A validated Rule instance.

    Raises:
        InputFailure: If validation fails.
    """
    _validate_rule_structure(rule)
    question_name = rule["question"]
    _validate_question_name(question_name, seen_names, questions)

    question = questions[question_name]
    pass_obj = rule["pass"]
    selected_kind = _validate_pass_object(pass_obj)

    # Validate based on kind
    minimum = None
    maximum = None
    choice = None
    min_confidence = None

    if selected_kind == "noul" and isinstance(question, Noul):
        minimum, maximum, _ = _parse_noul_predicate(pass_obj, question)
    elif selected_kind == "choice" and isinstance(question, Choice):
        choice, min_confidence = _parse_choice_predicate(pass_obj, question)
    elif selected_kind == "score" and isinstance(question, Score):
        minimum, maximum, min_confidence = _parse_score_predicate(pass_obj, question)
    else:
        raise InputFailure("--policy: predicate does not match question type")

    # Calculate score bounds for Score questions
    score_min = 0.0
    score_max = 0.0
    if selected_kind == "score" and isinstance(question, Score):
        score_min = 0.0
        score_max = float(len(question.criteria) - 1)

    return Rule(
        name=question_name,
        kind=selected_kind,
        minimum=minimum,
        maximum=maximum,
        choice=choice,
        min_confidence=min_confidence,
        score_min=score_min,
        score_max=score_max,
    )


def _validate_rule_structure(rule: dict[str, Any]) -> None:
    """Validate rule structure keys.

    Args:
        rule: The rule object to validate.

    Raises:
        InputFailure: If validation fails.
    """
    allowed_rule_keys = {"question", "pass"}
    for key in rule:
        if key not in allowed_rule_keys:
            raise InputFailure("--policy: rule has unknown field", code=1)

    if "question" not in rule:
        raise InputFailure("--policy: rule requires 'question' field", code=1)
    if "pass" not in rule:
        raise InputFailure("--policy: rule requires 'pass' field", code=1)


def _validate_question_name(
    question_name: str, seen_names: set[str], questions: Mapping[str, Question]
) -> None:
    """Require a nonempty, unique name that references a supplied question.

    Args:
        question_name: The question name to validate.
        seen_names: Set of already seen rule names.
        questions: Mapping of question names to Question instances.

    Raises:
        InputFailure: If validation fails.
    """
    if not isinstance(question_name, str) or question_name == "":
        raise InputFailure("--policy: question name must be a non-empty string", code=1)

    if question_name in seen_names:
        raise InputFailure("--policy: duplicate rule for question", code=1)

    if question_name not in questions:
        raise InputFailure("--policy: unknown question in rule", code=1)


def _validate_pass_object(pass_obj: dict[str, Any]) -> str:
    """Validate pass object and return selected kind.

    Args:
        pass_obj: The pass object to validate.

    Returns:
        The selected predicate kind ('noul', 'choice', or 'score').

    Raises:
        InputFailure: If validation fails.
    """
    if not isinstance(pass_obj, dict):
        raise InputFailure("--policy: pass must be an object", code=1)

    kinds = [key for key in pass_obj if key in {"noul", "choice", "score"}]
    if len(kinds) != 1:
        raise InputFailure("--policy: pass must have exactly one predicate type")
    kind = kinds[0]
    allowed = {kind} if kind == "noul" else {kind, "confidence"}
    if set(pass_obj) - allowed:
        raise InputFailure("--policy: pass has unknown or misplaced fields")
    return kind


def parse_policy(text: str, questions: Mapping[str, Question]) -> tuple[Rule, ...]:
    """Parse and validate policy JSON against typed questions.

    Args:
        text: Raw JSON policy text.
        questions: Mapping of question names to Question instances.

    Returns:
        Tuple of validated Rule instances.

    Raises:
        InputFailure: If policy is invalid, with sanitized diagnostics.
    """
    # Parse JSON with duplicate key detection
    try:
        data = json.loads(text, object_pairs_hook=_check_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise InputFailure(f"--policy: invalid JSON ({exc})", code=1) from None

    # Root must be an object
    if not isinstance(data, dict):
        raise InputFailure("--policy: root must be a JSON object", code=1)

    # Root must have exactly "rules" key
    if len(data) != 1 or "rules" not in data:
        raise InputFailure("--policy: root must have exactly 'rules' field", code=1)

    rules_obj = data["rules"]
    if not isinstance(rules_obj, list):
        raise InputFailure("--policy: rules must be an array", code=1)

    # Rules must be non-empty
    if len(rules_obj) == 0:
        raise InputFailure("--policy: rules array must not be empty", code=1)

    # Validate each rule
    seen_names: set[str] = set()
    result: list[Rule] = []

    for idx, rule in enumerate(rules_obj):
        if not isinstance(rule, dict):
            raise InputFailure(f"--policy: rules[{idx}] must be a JSON object", code=1)

        rule_obj = _validate_rule(rule, questions, seen_names)
        seen_names.add(rule_obj.name)
        result.append(rule_obj)

    return tuple(result)
