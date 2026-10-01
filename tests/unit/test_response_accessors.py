"""Prove typed response selection and shallow snapshot behavior.

Examples:
    Run the runtime and actual type-check regressions::

        uv run pytest -q tests/unit/test_response_accessors.py

See Also:
    - [judgevet.domain.response][]: Response container.
"""

import asyncio
import shutil
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest

from judgevet.domain.answers import ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.questions import Noul, Question
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.usage import Usage
from judgevet.media import ImageEvidence, judge_with_images

pytestmark = pytest.mark.unit


@pytest.fixture
def response() -> SystemOneResponse:
    """Return a mixed response with two answers of each variant.

    Returns:
        A response preserving deliberate interleaved insertion order.
    """
    return SystemOneResponse(
        model="fixture",
        usage=Usage(0, 0),
        answers={
            "n2": NoulAnswer(0.5),
            "c2": ChoiceAnswer("yes", 1.0, {"yes": 1.0}),
            "s2": ScoreAnswer(1.0, 1.0, {1: "one"}, {1: 1.0}),
            "n1": NoulAnswer(0.25),
            "c1": ChoiceAnswer("no", 1.0, {"no": 1.0}),
            "s1": ScoreAnswer(2.0, 1.0, {2: "two"}, {2: 1.0}),
        },
    )


@pytest.mark.parametrize(
    ("property_name", "keys"),
    [("nouls", ["n2", "n1"]), ("choices", ["c2", "c1"]), ("scores", ["s2", "s1"])],
)
def test_selection_identity_and_order(
    response: SystemOneResponse, property_name: str, keys: list[str]
) -> None:
    """Select exactly matching answers in order without copying their values."""
    selected = getattr(response, property_name)
    assert list(selected) == keys
    assert selected is not getattr(response, property_name)
    for key in keys:
        assert selected[key] is response.answers[key]


@pytest.mark.parametrize("property_name", ["nouls", "choices", "scores"])
def test_empty_and_missing(property_name: str) -> None:
    """Empty selections remain fresh plain dictionaries with normal KeyError."""
    response = SystemOneResponse("fixture", Usage(0, 0))
    selected = getattr(response, property_name)
    assert type(selected) is dict
    assert selected == {}
    assert selected is not getattr(response, property_name)
    with pytest.raises(KeyError, match="absent"):
        selected["absent"]


@pytest.mark.parametrize(
    ("property_name", "wrong_key"),
    [("nouls", "c2"), ("choices", "s2"), ("scores", "n2")],
)
def test_wrong_variant_key(
    response: SystemOneResponse, property_name: str, wrong_key: str
) -> None:
    """A key belonging to another variant is absent from this selection."""
    with pytest.raises(KeyError, match=wrong_key):
        getattr(response, property_name)[wrong_key]


@pytest.mark.parametrize(
    ("property_name", "key"), [("nouls", "n2"), ("choices", "c2"), ("scores", "s2")]
)
def test_mapping_mutations_are_independent(
    response: SystemOneResponse, property_name: str, key: str
) -> None:
    """Editing a returned mapping never changes the source dictionary."""
    original = response.answers
    before = dict(original)
    selected = getattr(response, property_name)
    selected["added"] = selected[key]
    selected[key] = response.answers["n1"]
    del selected[key]
    selected.clear()
    assert response.answers is original
    assert response.answers == before
    assert key in getattr(response, property_name)


@pytest.mark.parametrize(
    ("property_name", "key", "other"),
    [("nouls", "n2", "c2"), ("choices", "c2", "s2"), ("scores", "s2", "n2")],
)
def test_source_mutations_refresh_selection(
    response: SystemOneResponse, property_name: str, key: str, other: str
) -> None:
    """New reads see insertions, removals and variant replacements."""
    earlier = getattr(response, property_name)
    original = response.answers
    answer = original[key]
    original["added"] = answer
    assert getattr(response, property_name)["added"] is answer
    assert "added" not in earlier
    original[key] = original[other]
    assert key not in getattr(response, property_name)
    assert earlier[key] is answer
    del original["added"]
    assert "added" not in getattr(response, property_name)
    assert response.answers is original


def test_nested_values_remain_shared(response: SystemOneResponse) -> None:
    """Shallow selection preserves the existing nested-dictionary aliasing."""
    selected = response.choices
    selected["c2"].probabilities["yes"] = 0.5
    answer = response.answers["c2"]
    assert isinstance(answer, ChoiceAnswer)
    assert answer.probabilities["yes"] == 0.5


class _ReceiptProvider:
    """Return a provider-filled response from the text route.

    Attributes:
        response: The response every call returns.
    """

    def __init__(self, response: SystemOneResponse) -> None:
        """Keep the response to return."""
        self.response = response

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Return the provider-filled response."""
        return self.response


def test_receipts_default_and_survive() -> None:
    """Default receipts to empty and keep a provider's receipts on the response."""
    plain = SystemOneResponse(model="m", usage=Usage(0, 0))
    assert plain.receipts == {}
    receipt = {
        "off_option_mass": 0.125,
        "off_option_threshold": 0.25,
        "off_option_flag": False,
        "unmeasured": None,
    }
    filled = SystemOneResponse(
        model="m",
        usage=Usage(0, 0),
        answers={"claim": NoulAnswer(0.5)},
        receipts={"claim": receipt},
    )
    result = judge_with_images(
        _ReceiptProvider(filled),
        "state",
        {"claim": Noul(instructions="Is the claim supported?")},
        "selected",
        evidence=ImageEvidence([], {}),
    )
    assert result is filled
    assert result.receipts == {"claim": receipt}
    assert replace(filled, model="other").receipts == {"claim": receipt}
    assert replace(plain, receipts={"claim": receipt}) != plain
    with pytest.raises(FrozenInstanceError):
        filled.__setattr__("receipts", {})


async def _check_types(tmp_path: Path, valid: bool) -> None:
    """Run a real type checker against the selected probe.

    Args:
        tmp_path: Temporary probe directory.
        valid: Whether to omit the deliberately wrong assignment.
    """
    checker = shutil.which("ty")
    assert checker is not None
    source = """from typing import assert_type
from judgevet.domain.response import SystemOneResponse
from judgevet.domain.answers import NoulAnswer, ChoiceAnswer, ScoreAnswer

def read_answers(response: SystemOneResponse) -> tuple[float, str, float]:
    assert_type(response.nouls, dict[str, NoulAnswer])
    assert_type(response.choices, dict[str, ChoiceAnswer])
    assert_type(response.scores, dict[str, ScoreAnswer])
    return response.nouls["n"].noul, response.choices["c"].choice, response.scores["s"].score
"""
    if not valid:
        source += (
            "\ndef wrong(response: SystemOneResponse) -> None:\n"
            '    response.nouls["n"] = response.scores["s"]\n'
        )
    probe = tmp_path / "probe.py"
    probe.write_text(source, encoding="utf-8")
    project = Path(__file__).resolve().parents[2]
    process = await asyncio.create_subprocess_exec(
        checker,
        "check",
        "--project",
        str(project),
        str(probe),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    output = (stdout + stderr).decode()
    if valid:
        assert process.returncode == 0, output
    else:
        assert process.returncode != 0, output
        assert "invalid-argument-type" in output or "invalid-assignment" in output, (
            output
        )


@pytest.mark.parametrize("valid", [True, False])
def test_actual_type_checker(tmp_path: Path, valid: bool) -> None:
    """Check real typed field access and reject a deliberately wrong assignment."""
    asyncio.run(_check_types(tmp_path, valid))
