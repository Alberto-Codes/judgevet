"""Prove the acceptance pre-screen in examples/agent-hooks (#312).

The question file must parse as three Noul questions with true and false
criteria, and the policy must require each answer to reach 0.8. The state
builder must keep the changed-file list and the test hunks ahead of the
production hunks when it cuts the diff to its budget. No test here calls a
model; the provider is a fake port.
"""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from judgevet.domain.questions import Noul
from judgevet.policy import NoulRule
from tests.fixtures.providers import prescreen_provider

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "examples" / "agent-hooks"
SCRIPT = HOOKS / "prescreen.py"
QUESTIONS = HOOKS / "prescreen_questions.json"
PROVIDER = "tests.fixtures.providers.prescreen_provider"
SLICES = ROOT / "tests" / "fixtures" / "agent_hooks" / "prescreen_slices.jsonl"
INSTRUCTIONS = {
    "allowed_paths": "The diff changes only the allowed paths named in the contract",
    "tests_kept": "No existing test was weakened or removed",
    "test_fails_without": (
        "A new or changed test would fail without the production change"
    ),
}
SOURCE_HUNK = (
    "diff --git a/src/pkg/core.py b/src/pkg/core.py\n"
    "--- a/src/pkg/core.py\n+++ b/src/pkg/core.py\n"
    "@@ -1,2 +1,2 @@\n" + "".join(f"+source line {n}\n" for n in range(200))
)
TEST_HUNK = (
    "diff --git a/tests/unit/test_core.py b/tests/unit/test_core.py\n"
    "--- a/tests/unit/test_core.py\n+++ b/tests/unit/test_core.py\n"
    "@@ -1,1 +1,3 @@\n+def test_core():\n+    assert core() == 1\n-old line\n"
)
DIFF = SOURCE_HUNK + TEST_HUNK


def _load() -> ModuleType:
    """Import the pre-screen script from its path."""
    spec = importlib.util.spec_from_file_location("prescreen", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_question_file_holds_three_defined_noul_questions() -> None:
    """The shipped file parses as the three Noul questions in order."""
    questions = _load().load_questions(QUESTIONS)

    assert list(questions) == list(INSTRUCTIONS)
    for key, question in questions.items():
        assert isinstance(question, Noul)
        assert question.instructions == INSTRUCTIONS[key]
        assert question.criteria is not None
        assert set(question.criteria) == {"true", "false"}
        assert all(len(text.split()) >= 8 for text in question.criteria.values())


def test_question_file_refuses_a_question_that_is_not_noul(tmp_path: Path) -> None:
    """A choice question in the file raises ValueError naming its key."""
    path = tmp_path / "questions.json"
    path.write_text(
        json.dumps({"pick": {"type": "choice", "criteria": {"a": "A", "b": "B"}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="pick"):
        _load().load_questions(path)


def test_policy_requires_each_answer_to_reach_the_floor() -> None:
    """The policy holds one Noul rule with minimum 0.8 per question."""
    module = _load()
    policy = module.build_policy(module.load_questions(QUESTIONS), 0.8)

    assert [rule.name for rule in policy.rules] == list(INSTRUCTIONS)
    assert all(isinstance(rule, NoulRule) for rule in policy.rules)
    assert {rule.minimum for rule in policy.rules} == {0.8}


def test_trim_diff_keeps_the_file_list_and_test_hunks_first() -> None:
    """A cut diff starts with every path, then the test hunk, then source."""
    trimmed = _load().trim_diff(DIFF, 600)

    assert len(trimmed) <= 600
    files, _, rest = trimmed.partition("\n\n")
    assert "src/pkg/core.py (+200 -0)" in files
    assert "tests/unit/test_core.py (+2 -1)" in files
    assert rest.startswith("diff --git a/tests/unit/test_core.py")
    assert "+    assert core() == 1" in rest
    assert "source line 199" not in rest
    assert rest.endswith("[diff cut at the budget]")


def test_trim_diff_keeps_a_diff_that_fits_whole() -> None:
    """A diff within the budget keeps every hunk and has no cut marker."""
    trimmed = _load().trim_diff(DIFF, 100_000)

    assert "source line 199" in trimmed
    assert "[diff cut at the budget]" not in trimmed
    assert trimmed.index("test_core.py b/") < trimmed.index("core.py b/src")


def test_state_holds_contract_paths_diff_and_report() -> None:
    """The state names each part and cuts the report to its budget."""
    state = _load().build_state(
        contract="Add core.",
        allowed=["src/pkg/core.py", "tests/unit/test_core.py"],
        diff=DIFF,
        report="r" * 50,
        budgets={"contract": 100, "diff": 600, "report": 10},
    )

    assert list(state) == ["contract", "allowed_paths", "diff", "builder_report"]
    assert state["allowed_paths"] == "src/pkg/core.py\ntests/unit/test_core.py"
    assert state["diff"].startswith("Changed files:")
    assert state["builder_report"] == "r" * 10 + "\n[cut at the budget]"


def test_main_passes_when_every_answer_meets_the_floor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A confident fake port gives exit 0 and a passing JSON report."""
    code = _load().main(_argv(tmp_path, "confident"))

    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert report["passed"] is True
    assert report["answers"] == dict.fromkeys(INSTRUCTIONS, 0.9)
    call = prescreen_provider.CALLS[-1]
    state, _, _ = call
    assert isinstance(state, dict)
    assert "tests/unit/test_core.py" in state["diff"]


def test_main_fails_when_one_answer_is_below_the_floor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A doubtful fake port gives exit 1 and names the failing rule."""
    code = _load().main(_argv(tmp_path, "doubtful"))

    report = json.loads(capsys.readouterr().out)
    assert code == 1
    assert report["passed"] is False
    assert report["failed"] == ["test_fails_without"]


def test_slice_index_records_a_disposition_per_slice() -> None:
    """At least 10 slices carry a commit, a disposition and a provenance flag."""
    lines = SLICES.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]

    assert len(rows) >= 10
    for row in rows:
        assert set(row) == {"slice", "repo", "sha", "disposition", "reconstructed"}
        assert row["disposition"] in {"accept", "reject", "repair"}
        assert len(row["sha"]) >= 7
    assert len({row["slice"] for row in rows}) == len(rows)


def _argv(tmp_path: Path, factory: str) -> list[str]:
    """Write the slice inputs and return the command line."""
    (tmp_path / "contract.md").write_text("Add core.", encoding="utf-8")
    (tmp_path / "change.diff").write_text(DIFF, encoding="utf-8")
    (tmp_path / "report.txt").write_text("Done.", encoding="utf-8")
    return [
        "--provider",
        f"{PROVIDER}:{factory}",
        "--contract",
        str(tmp_path / "contract.md"),
        "--diff",
        str(tmp_path / "change.diff"),
        "--report",
        str(tmp_path / "report.txt"),
        "--allowed",
        "src/pkg/core.py",
    ]
