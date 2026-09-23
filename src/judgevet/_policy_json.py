"""Decode policy JSON outside the pure domain.

Examples:
    ```python
    from judgevet import Noul
    from judgevet._policy_json import parse_policy

    policy = parse_policy(
        '{"rules":[{"question":"q","pass":{"noul":{"min":0.5}}}]}',
        {"q": Noul()},
    )
    assert len(policy.rules) == 1
    ```

See Also:
    - [judgevet.policy_json][]: Supported JSON facade.
    - [judgevet.policy][]: Pure policy types and functions.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from judgevet.domain.questions import Choice, Noul, Question, Score
from judgevet.policy import (
    ChoiceRule,
    NoulRule,
    Policy,
    PolicyDefinitionError,
    Rule,
    ScoreRule,
    ValidatedPolicy,
    validate_policy,
)


def _check_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Check for duplicate keys in JSON object pairs.

    Args:
        pairs: Key-value pairs from JSON parsing.

    Returns:
        Pairs as dictionary.

    Raises:
        PolicyDefinitionError: If duplicate keys are found.
    """
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise PolicyDefinitionError("duplicate key in JSON object")
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
        PolicyDefinitionError: If validation fails.
    """
    allowed_keys = set()
    if allow_min:
        allowed_keys.add("min")
    if allow_max:
        allowed_keys.add("max")

    # Check for unknown keys
    for key in obj:
        if key not in allowed_keys:
            raise PolicyDefinitionError(f"{kind} predicate has unknown field")

    # Must have at least one bound
    if len(obj) == 0:
        raise PolicyDefinitionError(f"{kind} predicate requires at least one bound")

    minimum = _parse_bound(obj, "min", kind, min_bound, max_bound)
    maximum = _parse_bound(obj, "max", kind, min_bound, max_bound)

    # min <= max check
    if minimum is not None and maximum is not None and minimum > maximum:
        raise PolicyDefinitionError(f"{kind} min cannot exceed max")

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
        PolicyDefinitionError: If validation fails.
    """
    if bound_name not in obj:
        return None

    val = obj[bound_name]
    if not _is_finite_number(val):
        raise PolicyDefinitionError(f"{kind} {bound_name} must be a finite number")
    if val < min_bound or val > max_bound:
        raise PolicyDefinitionError(
            f"{kind} {bound_name} must be in [{min_bound}, {max_bound}]",
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
        PolicyDefinitionError: If validation fails.
    """
    if not isinstance(question, Noul):
        raise PolicyDefinitionError("question is not a noul type")

    # The noul predicate is the value of the 'noul' key
    if "noul" not in obj:
        raise PolicyDefinitionError("noul predicate requires 'noul' field")
    noul_obj = obj["noul"]
    if not isinstance(noul_obj, dict):
        raise PolicyDefinitionError("noul range must be an object")

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
        PolicyDefinitionError: If validation fails.
    """
    if not isinstance(question, Score):
        raise PolicyDefinitionError("question is not a score type")

    # The score predicate is the value of the 'score' key
    if "score" not in obj:
        raise PolicyDefinitionError("score predicate requires 'score' field")
    score_obj = obj["score"]
    if not isinstance(score_obj, dict):
        raise PolicyDefinitionError("score range must be an object")

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
            raise PolicyDefinitionError("confidence must be an object")

        # Confidence object must have exactly "min"
        if len(conf_obj) != 1 or "min" not in conf_obj:
            raise PolicyDefinitionError(
                "confidence object must have exactly 'min' field"
            )

        min_conf = conf_obj["min"]
        if not _is_finite_number(min_conf):
            raise PolicyDefinitionError(
                "confidence min must be a finite number, not bool or nonfinite",
            )
        if min_conf < 0.0 or min_conf > 1.0:
            raise PolicyDefinitionError("confidence min must be in [0.0, 1.0]")
        min_confidence = float(min_conf)

    return minimum, maximum, min_confidence


def _parse_choice_predicate(
    obj: dict[str, Any], question: Choice
) -> tuple[str, float | None]:
    """Parse and validate choice predicate.

    Args:
        obj: The pass object containing 'choice' and optionally 'confidence'.
        question: The Choice question.

    Returns:
        Tuple of (choice, min_confidence) values.

    Raises:
        PolicyDefinitionError: If validation fails.
    """
    if not isinstance(question, Choice):
        raise PolicyDefinitionError("question is not a choice type")

    known_keys = {"choice", "confidence"}
    for key in obj:
        if key not in known_keys:
            raise PolicyDefinitionError("choice predicate has unknown field")

    # Must have choice
    if "choice" not in obj:
        raise PolicyDefinitionError("choice predicate requires 'choice' field")

    choice_val = obj["choice"]
    if not isinstance(choice_val, str):
        raise PolicyDefinitionError("choice value must be a string")

    # Choice must exist in question criteria
    if choice_val not in question.criteria:
        raise PolicyDefinitionError("choice value not found in question criteria")

    # Parse optional confidence
    min_confidence = None
    if "confidence" in obj:
        conf_obj = obj["confidence"]
        if not isinstance(conf_obj, dict):
            raise PolicyDefinitionError("confidence must be an object")

        # Confidence object must have exactly "min"
        if len(conf_obj) != 1 or "min" not in conf_obj:
            raise PolicyDefinitionError(
                "confidence object must have exactly 'min' field"
            )

        min_conf = conf_obj["min"]
        if not _is_finite_number(min_conf):
            raise PolicyDefinitionError(
                "confidence min must be a finite number, not bool or nonfinite",
            )
        if min_conf < 0.0 or min_conf > 1.0:
            raise PolicyDefinitionError("confidence min must be in [0.0, 1.0]")
        min_confidence = float(min_conf)

    return choice_val, min_confidence


def _validate_rule(
    rule: dict[str, Any], questions: Mapping[str, Question], seen_names: set[str]
) -> Rule:
    """Decode one rule using the established grammar diagnostics.

    Args:
        rule: Decoded rule object.
        questions: Typed questions.
        seen_names: Previously used question names.

    Returns:
        The corresponding immutable typed rule.

    Raises:
        PolicyDefinitionError: If the rule fails schema or question validation.
    """
    _validate_rule_structure(rule)
    name = rule["question"]
    _validate_question_name(name, seen_names, questions)
    question = questions[name]
    predicate = rule["pass"]
    kind = _validate_pass_object(predicate)
    if kind == "noul" and isinstance(question, Noul):
        minimum, maximum, _ = _parse_noul_predicate(predicate, question)
        return NoulRule(name, minimum, maximum)
    if kind == "choice" and isinstance(question, Choice):
        choice, confidence = _parse_choice_predicate(predicate, question)
        return ChoiceRule(name, choice, confidence)
    if kind == "score" and isinstance(question, Score):
        minimum, maximum, confidence = _parse_score_predicate(predicate, question)
        return ScoreRule(name, minimum, maximum, confidence)
    raise PolicyDefinitionError("predicate does not match question type")


def _validate_rule_structure(rule: dict[str, Any]) -> None:
    """Validate rule structure keys.

    Args:
        rule: The rule object to validate.

    Raises:
        PolicyDefinitionError: If validation fails.
    """
    allowed_rule_keys = {"question", "pass"}
    for key in rule:
        if key not in allowed_rule_keys:
            raise PolicyDefinitionError("rule has unknown field")

    if "question" not in rule:
        raise PolicyDefinitionError("rule requires 'question' field")
    if "pass" not in rule:
        raise PolicyDefinitionError("rule requires 'pass' field")


def _validate_question_name(
    question_name: str, seen_names: set[str], questions: Mapping[str, Question]
) -> None:
    """Require a nonempty, unique name that references a supplied question.

    Args:
        question_name: The question name to validate.
        seen_names: Set of already seen rule names.
        questions: Mapping of question names to Question instances.

    Raises:
        PolicyDefinitionError: If validation fails.
    """
    if not isinstance(question_name, str) or question_name == "":
        raise PolicyDefinitionError("question name must be a non-empty string")

    if question_name in seen_names:
        raise PolicyDefinitionError("duplicate rule for question")

    if question_name not in questions:
        raise PolicyDefinitionError("unknown question in rule")


def _validate_pass_object(pass_obj: dict[str, Any]) -> str:
    """Validate pass object and return selected kind.

    Args:
        pass_obj: The pass object to validate.

    Returns:
        The selected predicate kind ('noul', 'choice', or 'score').

    Raises:
        PolicyDefinitionError: If validation fails.
    """
    if not isinstance(pass_obj, dict):
        raise PolicyDefinitionError("pass must be an object")

    kinds = [key for key in pass_obj if key in {"noul", "choice", "score"}]
    if len(kinds) != 1:
        raise PolicyDefinitionError("pass must have exactly one predicate type")
    kind = kinds[0]
    allowed = {kind} if kind == "noul" else {kind, "confidence"}
    if set(pass_obj) - allowed:
        raise PolicyDefinitionError("pass has unknown or misplaced fields")
    return kind


def parse_policy(text: str, questions: Mapping[str, Question]) -> ValidatedPolicy:
    """Parse and validate policy JSON against typed questions.

    Args:
        text: Raw JSON policy text.
        questions: Mapping of question names to Question instances.

    Returns:
        A validated immutable policy.

    Raises:
        PolicyDefinitionError: If policy is invalid, with sanitized diagnostics.
    """
    # Parse JSON with duplicate key detection
    try:
        data = json.loads(text, object_pairs_hook=_check_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise PolicyDefinitionError(f"invalid JSON ({exc})") from None

    # Root must be an object
    if not isinstance(data, dict):
        raise PolicyDefinitionError("root must be a JSON object")

    # Root must have exactly "rules" key
    if len(data) != 1 or "rules" not in data:
        raise PolicyDefinitionError("root must have exactly 'rules' field")

    rules_obj = data["rules"]
    if not isinstance(rules_obj, list):
        raise PolicyDefinitionError("rules must be an array")

    # Rules must be non-empty
    if len(rules_obj) == 0:
        raise PolicyDefinitionError("rules array must not be empty")

    # Validate each rule
    seen_names: set[str] = set()
    result: list[Rule] = []

    for idx, rule in enumerate(rules_obj):
        if not isinstance(rule, dict):
            raise PolicyDefinitionError(f"rules[{idx}] must be a JSON object")

        rule_obj = _validate_rule(rule, questions, seen_names)
        seen_names.add(rule_obj.name)
        result.append(rule_obj)

    return validate_policy(Policy(tuple(result)), questions)
