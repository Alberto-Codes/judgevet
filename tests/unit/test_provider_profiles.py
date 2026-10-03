"""Unit tests for the pre-call limits in judgevet.domain.provider_profiles."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from judgevet.domain.provider_errors import ProviderRequestError
from judgevet.domain.provider_profiles import (
    OLLAMA_PROFILE,
    ProviderProfile,
    check_profile,
)
from judgevet.domain.questions import Choice, Noul, Score

CANARY = "zz-criteria-canary"


def _labels(count: int) -> dict[str, str]:
    """Return `count` Choice criteria with text descriptions.

    Args:
        count: The number of options.

    Returns:
        Labels mapped to text descriptions.
    """
    return {f"opt{index}": f"{CANARY} {index}" for index in range(count)}


def _levels(count: int) -> list[str]:
    """Return `count` Score criteria with text descriptions.

    Args:
        count: The number of levels.

    Returns:
        Ordered text descriptions.
    """
    return [f"{CANARY} level {index}" for index in range(count)]


def _refused(questions: dict[str, Any]) -> str:
    """Require the Ollama profile to refuse the questions; return the message.

    Args:
        questions: Question names mapped to typed or raw questions.

    Returns:
        The error message.
    """
    with pytest.raises(ProviderRequestError) as info:
        check_profile(questions, OLLAMA_PROFILE)
    return str(info.value)


@pytest.mark.unit
def test_ollama_profile_values() -> None:
    """The Ollama profile carries the documented limits and its source."""
    expected = ProviderProfile(
        name="ollama",
        choice_options=(2, 26),
        score_levels=(2, 26),
        text_criteria_only=True,
        source_url="https://docs.ollama.com/api/systemone",
        verified_version="v0.35.1",
    )
    assert expected == OLLAMA_PROFILE
    field = "name"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(OLLAMA_PROFILE, field, "other")


@pytest.mark.unit
@pytest.mark.parametrize("count", [27, 1])
def test_choice_option_count_outside_range_is_refused(count: int) -> None:
    """A typed Choice with 27 or 1 options is refused."""
    message = _refused({"queue": Choice(criteria=_labels(count))})
    assert "'queue'" in message
    assert "'ollama'" in message


@pytest.mark.unit
@pytest.mark.parametrize("count", [26, 2])
def test_choice_option_count_inside_range_is_accepted(count: int) -> None:
    """A typed Choice with 26 or 2 text options passes the check."""
    assert (
        check_profile({"queue": Choice(criteria=_labels(count))}, OLLAMA_PROFILE)
        is None
    )


@pytest.mark.unit
@pytest.mark.parametrize("count", [27, 1])
def test_raw_choice_option_count_outside_range_is_refused(count: int) -> None:
    """A raw Choice mapping is counted the same way as a typed one."""
    raw = {"type": "choice", "criteria": _labels(count)}
    assert "'queue'" in _refused({"queue": raw})


@pytest.mark.unit
@pytest.mark.parametrize("count", [27, 1])
def test_score_level_count_outside_range_is_refused(count: int) -> None:
    """A typed Score with 27 or 1 levels is refused."""
    message = _refused({"tone": Score(criteria=_levels(count))})
    assert "'tone'" in message
    assert "'ollama'" in message


@pytest.mark.unit
@pytest.mark.parametrize("count", [26, 2])
def test_score_level_count_inside_range_is_accepted(count: int) -> None:
    """A typed Score with 26 or 2 text levels passes the check."""
    assert (
        check_profile({"tone": Score(criteria=_levels(count))}, OLLAMA_PROFILE) is None
    )


@pytest.mark.unit
@pytest.mark.parametrize("count", [27, 1])
def test_raw_score_level_count_outside_range_is_refused(count: int) -> None:
    """A raw Score mapping is counted the same way as a typed one."""
    raw = {"type": "score", "criteria": _levels(count)}
    assert "'tone'" in _refused({"tone": raw})


@pytest.mark.unit
def test_object_choice_criteria_is_refused() -> None:
    """A Choice description that is an object is refused under text-only."""
    criteria: dict[str, Any] = {"a": "Text", "b": {"covers": CANARY}}
    message = _refused({"queue": Choice(criteria=criteria)})
    assert "'queue'" in message
    assert "'ollama'" in message


@pytest.mark.unit
def test_array_and_raw_object_criteria_are_refused() -> None:
    """Array descriptions and raw object descriptions are refused too."""
    assert "'tone'" in _refused({"tone": Score(criteria=["Poor", [CANARY, "Good"]])})
    raw_score = {"type": "score", "criteria": ["Poor", {"x": CANARY}]}
    assert "'tone'" in _refused({"tone": raw_score})
    raw_choice = {"type": "choice", "criteria": {"a": "A", "b": [CANARY]}}
    assert "'queue'" in _refused({"queue": raw_choice})


@pytest.mark.unit
def test_text_and_none_choice_criteria_are_accepted() -> None:
    """Text descriptions and undescribed labels pass the text-only check."""
    questions = {"queue": Choice(criteria={"a": "Text", "b": None, "c": "More"})}
    assert check_profile(questions, OLLAMA_PROFILE) is None


@pytest.mark.unit
def test_object_criteria_allowed_when_profile_allows_them() -> None:
    """A profile without the text-only rule accepts object descriptions."""
    lenient = dataclasses.replace(OLLAMA_PROFILE, text_criteria_only=False)
    criteria: dict[str, Any] = {"a": "Text", "b": {"covers": CANARY}}
    assert check_profile({"queue": Choice(criteria=criteria)}, lenient) is None


@pytest.mark.unit
def test_message_is_value_free() -> None:
    """The message names the key and the profile, never criteria or labels."""
    criteria: dict[str, Any] = {"labelcanary": {"covers": CANARY}, "b": "Text"}
    messages = [
        _refused({"queue": Choice(criteria=_labels(27))}),
        _refused({"queue": Choice(criteria=criteria)}),
        _refused({"queue": Score(criteria=_levels(1))}),
    ]
    for message in messages:
        assert "'queue'" in message
        assert "'ollama'" in message
        assert CANARY not in message
        assert "labelcanary" not in message
        assert "opt0" not in message


@pytest.mark.unit
def test_long_key_is_truncated_to_80_characters() -> None:
    """A long question key is truncated as the Choice option check does."""
    key = "k" * 200
    message = _refused({key: Choice(criteria=_labels(27))})
    assert repr("k" * 80) in message
    assert "k" * 81 not in message


@pytest.mark.unit
def test_none_profile_checks_nothing() -> None:
    """A None profile accepts any count and any description form."""
    criteria: dict[str, Any] = {"b": {"covers": CANARY}}
    questions = {
        "queue": Choice(criteria=_labels(27) | criteria),
        "tone": Score(criteria=_levels(1)),
    }
    assert check_profile(questions, None) is None


@pytest.mark.unit
def test_noul_and_unknown_questions_are_not_checked() -> None:
    """Noul questions and raw mappings without countable criteria pass."""
    questions = {
        "billing": Noul(instructions={"text": CANARY}),
        "raw_noul": {"type": "noul", "criteria": {"true": {"x": CANARY}}},
        "no_criteria": {"type": "choice"},
        "bad_score": {"type": "score", "criteria": "not a list"},
        "other": "not a mapping",
    }
    assert check_profile(questions, OLLAMA_PROFILE) is None
