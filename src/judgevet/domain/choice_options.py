"""Check Choice answers against the options their questions offered.

A Choice question offers the keys of its criteria. An answer whose `choice`
or a probability key falls outside those keys cannot belong to the question,
so the check rejects the response. Probability keys may cover a subset of the
criteria. The options come from the question's `criteria` mapping, per
https://docs.typesafe.ai/primitives/choice#structured-instructions-and-criteria.

Examples:
    ```python
    from judgevet.domain.answers import ChoiceAnswer
    from judgevet.domain.choice_options import check_choice_options
    from judgevet.domain.errors import JevResponseError
    from judgevet.domain.questions import Choice

    questions = {"queue": Choice(criteria={"billing": None, "technical": None})}
    listed = ChoiceAnswer("billing", 1.0, {"billing": 1.0})
    check_choice_options(questions, {"queue": listed})
    off_list = ChoiceAnswer("sales", 1.0, {"sales": 1.0})
    try:
        check_choice_options(questions, {"queue": off_list})
    except JevResponseError as exc:
        assert exc.status_code == 200
    else:
        raise AssertionError("an off-list option must raise")
    ```

See Also:
    - [judgevet.domain.questions.Choice][]: The question that offers the options
    - [judgevet.domain.answers.ChoiceAnswer][]: The answer the check reads
    - [judgevet.domain.errors.JevResponseError][]: The error the check raises
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from judgevet.domain.answers import Answer, ChoiceAnswer
from judgevet.domain.errors import JevResponseError
from judgevet.domain.questions import Choice


def _options(question: Any) -> set[str] | None:
    """Return the labels a Choice question offers, or None when unknown.

    Args:
        question: A typed question or a raw question mapping.

    Returns:
        The criteria keys of a Choice question, or None for any other question.
    """
    if isinstance(question, Choice):
        return set(question.criteria)
    if isinstance(question, Mapping) and question.get("type") == "choice":
        criteria = question.get("criteria")
        if isinstance(criteria, Mapping):
            return set(criteria)
    return None


def check_choice_options(
    questions: Mapping[str, Any], answers: Mapping[str, Answer]
) -> None:
    """Reject a Choice answer that names an option its question did not offer.

    Answers with no matching question, non-Choice answers and questions
    without mapping criteria go unchecked.

    Args:
        questions: Question names mapped to typed or raw questions.
        answers: Answer names mapped to parsed answers.

    Raises:
        JevResponseError: If a Choice answer's `choice` or a probability key
            is not a criteria key of its question. The status code is 200.
    """
    for name, answer in answers.items():
        if not isinstance(answer, ChoiceAnswer) or name not in questions:
            continue
        options = _options(questions[name])
        if options is None:
            continue
        for option in (answer.choice, *answer.probabilities):
            if option not in options:
                raise JevResponseError(
                    f"Invalid choice answer for question {name[:80]!r}: "
                    f"option {option[:80]!r} is not in the question's criteria",
                    200,
                )
