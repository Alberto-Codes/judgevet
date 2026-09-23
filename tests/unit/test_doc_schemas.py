"""Acceptance tests for documented JSON against shipped input contracts."""

import importlib

import pytest
from jsonschema.exceptions import ValidationError


def test_mcp_arguments_match_discovery() -> None:
    checker = importlib.import_module("scripts.doc_schema_child")
    outcome = checker.validate_mcp(
        '{"state":"Synthetic text","instruction":"Is it clear?"}'
    )
    assert outcome is None


@pytest.mark.parametrize(
    "text",
    [
        '{"state":[] ,"instruction":"Question?"}',
        '{"state":"text"}',
        '{"state":"text","instruction":42}',
    ],
)
def test_mcp_schema_rejects_invalid_arguments(text: str) -> None:
    checker = importlib.import_module("scripts.doc_schema_child")
    with pytest.raises(ValidationError):
        checker.validate_mcp(text)


def test_policy_fragment_is_validated_in_documented_context() -> None:
    checker = importlib.import_module("scripts.doc_schema_child")
    checker.validate_fragment('{"question":"risk","pass":{"choice":"low"}}')
    with pytest.raises(ValueError):
        checker.validate_fragment('{"question":"risk","pass":{"choice":"unknown"}}')


def test_question_json_rejects_duplicate_keys() -> None:
    checker = importlib.import_module("scripts.doc_schema_child")
    with pytest.raises(ValueError):
        checker.validate_questions('{"q":{"type":"noul","type":"choice"}}')
