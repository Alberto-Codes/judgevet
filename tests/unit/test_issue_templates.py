"""Keep issue intake requirements aligned with the acceptance contract."""

import re
from pathlib import Path

import pytest
import yaml

TEMPLATES = Path(__file__).resolve().parents[2] / ".github/ISSUE_TEMPLATE"
REQUIRED = {
    "task": ("do", "do-not", "prove"),
    "setup": (
        "host",
        "environment",
        "installation",
        "configuration",
        "reproduction",
        "expected",
        "observed",
        "prove",
    ),
}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("form", "field"),
    [(form, field) for form, fields in REQUIRED.items() for field in fields],
)
def test_required_evidence_cannot_be_optional_or_prefilled(form: str, field: str):
    template = yaml.safe_load((TEMPLATES / f"{form}.yml").read_text())
    matching = [entry for entry in template["body"] if entry.get("id") == field]
    assert len(matching) == 1
    entry = matching[0]
    assert entry["type"] in {"input", "textarea"}
    assert entry["validations"]["required"] is True
    assert not entry["attributes"].get("value")
    assert entry["attributes"]["label"]
    assert entry["attributes"]["description"]


@pytest.mark.unit
@pytest.mark.parametrize("form", REQUIRED)
def test_forms_have_valid_unique_fields_and_guidance(form: str):
    template = yaml.safe_load((TEMPLATES / f"{form}.yml").read_text())
    assert template["name"] and template["description"]
    ids = []
    guidance = []
    for entry in template["body"]:
        assert entry["type"] in {"markdown", "input", "textarea"}
        if entry["type"] == "markdown":
            guidance.append(entry["attributes"]["value"])
        else:
            assert re.fullmatch(r"[a-zA-Z0-9_-]+", entry["id"])
            ids.append(entry["id"])
    assert len(ids) == len(set(ids))
    text = "\n".join(guidance)
    assert "CONTRIBUTING.md" in text
    assert "contributor-setup" in text
    assert "security/advisories/new" in text


@pytest.mark.unit
def test_chooser_requires_a_form_and_offers_private_security_reporting():
    configuration = yaml.safe_load((TEMPLATES / "config.yml").read_text())
    assert configuration["blank_issues_enabled"] is False
    assert any(
        link["url"]
        == "https://github.com/Alberto-Codes/judgevet/security/advisories/new"
        for link in configuration["contact_links"]
    )
    assert {p.name for p in TEMPLATES.glob("*.yml")} == {
        "task.yml",
        "setup.yml",
        "config.yml",
    }
