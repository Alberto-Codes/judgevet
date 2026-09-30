"""Pin the provider-equivalence sentence on the self-hosted provider page."""

from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[2] / "docs/how-to/use-a-self-hosted-provider.md"
SENTENCE = (
    "**A provider that satisfies `SystemOnePort` is compatible in shape, "
    "not equivalent in judgment.**"
)


def assert_states_equivalence_limit(page: Path) -> None:
    """Fail unless the page carries the exact provider-equivalence sentence.

    Args:
        page: The Markdown source file to read.

    Raises:
        AssertionError: The page lacks the sentence, markup included.
    """
    text = page.read_text(encoding="utf-8")
    assert SENTENCE in text, f"{page.name} is missing the sentence: {SENTENCE}"


@pytest.mark.unit
def test_self_hosted_page_states_shape_is_not_judgment():
    assert_states_equivalence_limit(PAGE)
