"""Acceptance tests for glossary-driven, contextual terminology enforcement."""

import importlib
from pathlib import Path

import pytest

GLOSSARY = Path("docs/reference/glossary.md")


@pytest.mark.parametrize(
    ("text", "preferred"),
    [
        ("Send the prompt to Jev.", "question"),
        ("A Noul result contains a probability.", "answer"),
        ("Choice certainty is separate from its label.", "confidence"),
        ("Use the judgevet interface.", "port"),
        ("Use the HTTP driver.", "adapter"),
        ("It provides a calibrated judgment.", "model judgment"),
    ],
)
def test_contextual_prose_rejected(text: str, preferred: str) -> None:
    checker = importlib.import_module("scripts.check_terminology")
    findings = checker.prose_findings(text, checker.read_rules(GLOSSARY))
    assert len(findings) == 1
    assert preferred in findings[0]


@pytest.mark.parametrize(
    "text",
    [
        "The HTTP response contains answers.",
        "The function result is returned.",
        "The result is available.",
        "Read `SystemOneResponse` and the `result` wire field.",
        "Enter a key at the Bash prompt.",
        "Use [the API](https://example.com/calibrated-judgment).",
        "The diagnostic is `Noul result missing`.",
        "```text\nA calibrated judgment.\n```",
    ],
)
def test_literal_and_ambiguous_contexts_remain_valid(text: str) -> None:
    checker = importlib.import_module("scripts.check_terminology")
    assert checker.prose_findings(text, checker.read_rules(GLOSSARY)) == []


def test_glossary_controls_replacement(tmp_path: Path) -> None:
    checker = importlib.import_module("scripts.check_terminology")
    changed = tmp_path / "glossary.md"
    changed.write_text(
        GLOSSARY.read_text().replace("| question |", "| instruction |", 1)
    )
    findings = checker.prose_findings(
        "Send the prompt to Jev.", checker.read_rules(changed)
    )
    assert len(findings) == 1
    assert "instruction" in findings[0]


def test_typed_local_is_checked_but_contract_names_remain() -> None:
    checker = importlib.import_module("scripts.check_terminology")
    source = """from judgevet import Noul, SystemOneResponse

def public(response: SystemOneResponse) -> SystemOneResponse:
    prompt: Noul = Noul()
    result: SystemOneResponse = response
    return result
"""
    findings = checker.identifier_findings(source, checker.read_rules(GLOSSARY))
    assert len(findings) == 1
    assert "4:" in findings[0]
    assert "question" in findings[0]


def test_unrelated_type_is_not_domain_vocabulary() -> None:
    checker = importlib.import_module("scripts.check_terminology")
    source = "from another_package import Noul\ndef run():\n    prompt: Noul\n"
    assert checker.identifier_findings(source, checker.read_rules(GLOSSARY)) == []


@pytest.mark.parametrize(
    "source",
    [
        "from judgevet import Noul\nprompt: Noul\n",
        "from judgevet import Noul\nclass Public:\n    prompt: Noul\n",
        "from judgevet import Noul\ndef public(prompt: Noul):\n    return prompt\n",
    ],
)
def test_public_contract_names_are_preserved(source: str) -> None:
    checker = importlib.import_module("scripts.check_terminology")
    assert checker.identifier_findings(source, checker.read_rules(GLOSSARY)) == []


def test_aliased_individual_answer_annotation_is_checked() -> None:
    checker = importlib.import_module("scripts.check_terminology")
    source = "from judgevet import NoulAnswer as NA\ndef run():\n    result: NA\n"
    findings = checker.identifier_findings(source, checker.read_rules(GLOSSARY))
    assert len(findings) == 1
    assert "answer" in findings[0]
