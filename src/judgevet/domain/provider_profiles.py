"""Check a request against the documented limits of one compatible server.

A provider profile records the question limits a server documents. The Jev
API has no 26-option maximum, so a profile is opt-in. A caller passes one to
the hosted adapter or the fakes. `check_profile` refuses a breach before any
request. The refusal names the question key and the profile, never the
criteria text or the option labels.

Attributes:
    OLLAMA_PROFILE (ProviderProfile): Ollama's `POST /v1/systemone` limits,
        per https://docs.ollama.com/api/systemone, verified on v0.35.1.

Examples:
    ```python
    from judgevet.domain.provider_errors import ProviderRequestError
    from judgevet.domain.provider_profiles import OLLAMA_PROFILE, check_profile
    from judgevet.domain.questions import Choice

    check_profile({"queue": Choice(criteria={"a": "A", "b": "B"})}, OLLAMA_PROFILE)
    try:
        check_profile({"queue": Choice(criteria={"a": "A"})}, OLLAMA_PROFILE)
    except ProviderRequestError as exc:
        assert "'ollama'" in str(exc)
    else:
        raise AssertionError("a one-option Choice must raise")
    ```

See Also:
    - [judgevet.domain.questions][]: The Choice and Score questions it checks
    - [judgevet.domain.provider_errors.ProviderRequestError][]: The refusal
    - [judgevet.domain.choice_options][]: The key truncation it follows
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from judgevet.domain.provider_errors import ProviderRequestError
from judgevet.domain.questions import Choice, Score

__all__ = ["OLLAMA_PROFILE", "ProviderProfile", "check_profile"]


@dataclass(frozen=True)
class ProviderProfile:
    """The documented question limits of one compatible server.

    Attributes:
        name (str): The profile name the refusal message carries.
        choice_options (tuple[int, int]): Inclusive minimum and maximum
            number of Choice options.
        score_levels (tuple[int, int]): Inclusive minimum and maximum number
            of Score levels.
        text_criteria_only (bool): True when every Choice or Score
            description must be text. A Choice label with no description
            passes.
        source_url (str): The page that documents the limits.
        verified_version (str): The server version a call verified.

    Examples:
        ```python
        profile = ProviderProfile("demo", (2, 4), (2, 4), False, "https://x", "v1")
        assert profile.choice_options == (2, 4)
        ```
    """

    name: str
    choice_options: tuple[int, int]
    score_levels: tuple[int, int]
    text_criteria_only: bool
    source_url: str
    verified_version: str


OLLAMA_PROFILE = ProviderProfile(
    name="ollama",
    choice_options=(2, 26),
    score_levels=(2, 26),
    text_criteria_only=True,
    source_url="https://docs.ollama.com/api/systemone",
    verified_version="v0.35.1",
)
"""Ollama's decision-model limits: 2 to 26 options and levels, text only."""


def _descriptions(question: Any) -> tuple[str, list[Any]] | None:
    """Return the question kind and its criteria descriptions.

    Args:
        question: A typed question or a raw question mapping.

    Returns:
        `("choice", descriptions)` or `("score", descriptions)`, or None for
        a Noul or for a question whose criteria cannot be counted.
    """
    if isinstance(question, Choice):
        return "choice", list(question.criteria.values())
    if isinstance(question, Score):
        return "score", list(question.criteria)
    if not isinstance(question, Mapping):
        return None
    kind = question.get("type")
    criteria = question.get("criteria")
    if kind == "choice" and isinstance(criteria, Mapping):
        return "choice", list(criteria.values())
    if kind == "score" and isinstance(criteria, Sequence):
        return None if isinstance(criteria, str) else ("score", list(criteria))
    return None


def _breach(kind: str, descriptions: list[Any], profile: ProviderProfile) -> str:
    """Return the value-free rule the descriptions break, or an empty string.

    Args:
        kind: `choice` or `score`.
        descriptions: The question's criteria descriptions.
        profile: The profile to check against.

    Returns:
        A short rule description, or an empty string when the question passes.
    """
    low, high = profile.choice_options if kind == "choice" else profile.score_levels
    noun = "option" if kind == "choice" else "level"
    if not low <= len(descriptions) <= high:
        return f"its {noun} count is outside {low} to {high}"
    allowed = (str, type(None)) if kind == "choice" else (str,)
    if profile.text_criteria_only and not all(
        isinstance(entry, allowed) for entry in descriptions
    ):
        return "a criteria description is not text"
    return ""


def check_profile(
    questions: Mapping[str, Any], profile: ProviderProfile | None
) -> None:
    """Refuse a Choice or Score question that breaks the profile's limits.

    Typed and raw questions are checked. Noul questions, instructions and raw
    questions without countable criteria go unchecked. A None profile checks
    nothing.

    Args:
        questions: Question names mapped to typed or raw questions.
        profile: The server profile, or None for no check.

    Raises:
        ProviderRequestError: If a Choice option count or a Score level count
            is outside the profile's range, or a description is not text
            under a text-only profile. The message names the question key,
            truncated to 80 characters, and the profile name only.
    """
    if profile is None:
        return
    for name, question in questions.items():
        found = _descriptions(question)
        if found is None:
            continue
        rule = _breach(*found, profile)
        if rule:
            raise ProviderRequestError(
                f"Question {name[:80]!r} breaks the {profile.name!r} "
                f"provider profile: {rule}"
            )
