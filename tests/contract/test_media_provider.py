"""Prove a repository-owned translating adapter and fake preserve media contracts.

Examples:
    Run the focused pytest module from the repository root.

See Also:
    - [judgevet.media][]: Public media contract.
"""

from collections.abc import Mapping
from typing import Any

import pytest

from judgevet import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    SystemOneResponse,
    Usage,
)
from judgevet.media import (
    ImageAttachment,
    ImageEvidence,
    MediaCapabilities,
    judge_with_images,
)

pytestmark = pytest.mark.contract


class FixtureBackend:
    """Inspect a neutral external payload before returning a translated result.

    Attributes:
        payloads (list): Captured independent payload assertions.

    Examples:
        Exercise this offline fixture through the tests in this module.
    """

    def __init__(self) -> None:
        """Initialize captured payloads."""
        self.payloads: list[dict[str, Any]] = []

    def judge(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Assert the complete media payload, independently of result fixtures.

        Returns:
            The offline fixture value.
        """
        assert payload["state"] == {"document": ["ordered", "input"]}
        assert payload["model"] == "chosen-model"
        assert payload["images"] == [
            ("scan-a", b"\x00exact-a\xff", "image/png"),
            ("scan-b", b"\xffexact-b\x00", "image/jpeg"),
        ]
        assert payload["bindings"] == {
            "truth-id": ("scan-b", "scan-a"),
            "choice-id": ("scan-a",),
            "score-id": ("scan-b",),
        }
        assert payload["required"] == frozenset({"truth-id", "choice-id"})
        assert payload["questions"] == {
            "truth-id": {
                "type": "noul",
                "instructions": {"check": ["visible"]},
                "criteria": None,
            },
            "choice-id": {
                "type": "choice",
                "instructions": ["choose exactly"],
                "criteria": {"yes": "present", "no": "absent"},
            },
            "score-id": {
                "type": "score",
                "instructions": "rate evidence",
                "criteria": ["clear", "complete"],
            },
        }
        self.payloads.append(payload)
        return {
            "truth": 0.7,
            "choice": "yes",
            "score": 0.6,
            "model": "resolved-model",
            "tokens": 0,
        }


class TranslatingProvider:
    """Translate generic typed requests to an independently checked wire shape.

    Attributes:
        backend (FixtureBackend): Offline translation backend.

    Examples:
        Exercise this offline fixture through the tests in this module.
    """

    def __init__(self) -> None:
        """Initialize the offline translation backend."""
        self.backend = FixtureBackend()

    def capabilities(self, model: str) -> MediaCapabilities:
        """Declare supported formats for the selected fixture model.

        Returns:
            The offline fixture value.
        """
        assert model == "chosen-model"
        return MediaCapabilities({"image/png", "image/jpeg"})

    def system_one(self, state, questions, model) -> SystemOneResponse:
        """Reject a hidden text conversion in this media-only probe."""
        pytest.fail("media request reached the text method")

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Preserve submitted values in an application-owned translation.

        Returns:
            The offline fixture value.
        """
        definitions = {}
        for name, question in questions.items():
            definitions[name] = (
                dict(question)
                if isinstance(question, Mapping)
                else {
                    "type": "noul"
                    if isinstance(question, Noul)
                    else "choice"
                    if isinstance(question, Choice)
                    else "score",
                    "instructions": question.instructions,
                    "criteria": question.criteria,
                }
            )
        result = self.backend.judge(
            {
                "state": state,
                "model": model,
                "questions": definitions,
                "images": [
                    (item.id, item.data, item.media_type) for item in evidence.images
                ],
                "bindings": dict(evidence.by_question),
                "required": evidence.required,
            }
        )
        return SystemOneResponse(
            result["model"],
            Usage(result["tokens"], None),
            {
                "truth-id": NoulAnswer(result["truth"]),
                "choice-id": ChoiceAnswer(
                    result["choice"], 0.8, {"yes": 0.8, "no": 0.2}
                ),
                "score-id": ScoreAnswer(
                    result["score"], 0.8, {0: "clear", 1: "complete"}, {0: 0.4, 1: 0.6}
                ),
            },
        )


class FakeProvider(TranslatingProvider):
    """Return the same typed fixture while independently checking submitted evidence.

    Examples:
        Exercise this offline fixture through the tests in this module.
    """

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Assert media delivery before returning the offline answer fixture.

        Returns:
            The offline fixture value.
        """
        assert [item.data for item in evidence.images] == [
            b"\x00exact-a\xff",
            b"\xffexact-b\x00",
        ]
        assert evidence.by_question["truth-id"] == ("scan-b", "scan-a")
        assert model == "chosen-model"
        assert state == {"document": ["ordered", "input"]}
        assert set(questions) == {"truth-id", "choice-id", "score-id"}
        return SystemOneResponse(
            "resolved-model",
            Usage(0, None),
            {
                "truth-id": NoulAnswer(0.7),
                "choice-id": ChoiceAnswer("yes", 0.8, {"yes": 0.8, "no": 0.2}),
                "score-id": ScoreAnswer(
                    0.6, 0.8, {0: "clear", 1: "complete"}, {0: 0.4, 1: 0.6}
                ),
            },
        )


@pytest.mark.parametrize("raw", [False, True])
def test_fake_and_translator_agree_on_exact_media(raw: bool) -> None:
    """Exercise all variants, exact bytes, associations and available metadata."""
    definitions: dict[str, Question | Mapping[str, Any]] = {
        "truth-id": Noul(instructions={"check": ["visible"]}),
        "choice-id": Choice(
            criteria={"yes": "present", "no": "absent"}, instructions=["choose exactly"]
        ),
        "score-id": Score(criteria=["clear", "complete"], instructions="rate evidence"),
    }
    if raw:
        definitions["score-id"] = {
            "type": "score",
            "instructions": "rate evidence",
            "criteria": ["clear", "complete"],
        }
    submitted = ImageEvidence(
        [
            ImageAttachment("scan-a", b"\x00exact-a\xff", "image/png"),
            ImageAttachment("scan-b", b"\xffexact-b\x00", "image/jpeg"),
        ],
        {
            "truth-id": ["scan-b", "scan-a"],
            "choice-id": ["scan-a"],
            "score-id": ["scan-b"],
        },
        {"truth-id", "choice-id"},
    )
    state = {"document": ["ordered", "input"]}
    fake = judge_with_images(
        FakeProvider(), state, definitions, "chosen-model", evidence=submitted
    )
    translator = TranslatingProvider()
    actual = judge_with_images(
        translator, state, definitions, "chosen-model", evidence=submitted
    )
    assert actual == fake
    assert len(translator.backend.payloads) == 1
    assert actual.usage == Usage(0, None)
    assert actual.model == "resolved-model"
