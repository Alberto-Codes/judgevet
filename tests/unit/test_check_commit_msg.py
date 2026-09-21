"""Tests for the commit message gate."""

from scripts.check_commit_msg import message_lines, problems, subject_problems


class TestMessageLines:
    """Tests for message_lines()."""

    def test_strips_comment_lines(self) -> None:
        """Comment lines starting with # are removed."""
        text = "feat: add feature\n# This is a comment\n\nMore text"
        assert message_lines(text) == ["feat: add feature", "", "More text"]

    def test_strips_trailing_blank_lines(self) -> None:
        """Trailing blank lines are removed."""
        text = "feat: add feature\n\n"
        assert message_lines(text) == ["feat: add feature"]

    def test_scissors_line_cuts_off_rest(self) -> None:
        """Lines after scissors line are discarded."""
        text = "feat: add feature\n# --- >8 ---\nhidden"
        assert message_lines(text) == ["feat: add feature"]


class TestSubjectProblems:
    """Tests for subject_problems()."""

    def test_valid_subject(self) -> None:
        """A valid subject returns no problems."""
        assert subject_problems("feat: add feature") == []
        assert subject_problems("fix: resolve bug") == []
        assert subject_problems("feat(cli): add flag") == []

    def test_empty_subject(self) -> None:
        """Empty subject fails."""
        assert "the subject is not" in subject_problems("")[0]

    def test_invalid_type(self) -> None:
        """Unknown type fails."""
        problems = subject_problems("unknown: something")
        assert "the type 'unknown' is not one of" in problems[0]

    def test_empty_scope(self) -> None:
        """Empty scope warns."""
        problems = subject_problems("feat(): add feature")
        assert "the scope is empty" in problems[0]

    def test_trailing_dot(self) -> None:
        """Description ending with a period warns."""
        problems = subject_problems("feat: add feature.")
        assert "the description ends with a period" in problems[0]

    def test_empty_description(self) -> None:
        """Empty description after colon fails."""
        problems = subject_problems("feat: ")
        assert "the description is empty" in problems[0]


class TestProblems:
    """Tests for problems()."""

    def test_merge_commit_skipped(self) -> None:
        """Merge commits are skipped."""
        text = 'Merge branch "feature"\n'
        found, has_issue = problems(text)
        assert found == []
        assert has_issue is False

    def test_fixup_commit_skipped(self) -> None:
        """Fixup commits are skipped."""
        text = "fixup! feat: add feature\n"
        found, has_issue = problems(text)
        assert found == []
        assert has_issue is False

    def test_revert_commit_skipped(self) -> None:
        """Revert commits are skipped."""
        text = 'Revert "feat: add feature"\n'
        found, has_issue = problems(text)
        assert found == []
        assert has_issue is False

    def test_non_conforming_subject_fails(self) -> None:
        """Non-conforming subject fails."""
        text = "This is not a conventional commit\n"
        found, _ = problems(text)
        assert len(found) > 0
        assert "the subject is not" in found[0]

    def test_missing_issue_reference_warns(self) -> None:
        """Feat without Closes/Refs gets warning, not failure."""
        text = "feat: add feature\n\nSome description"
        found, has_issue = problems(text)
        assert found == []
        assert has_issue is False

    def test_with_issue_reference(self) -> None:
        """Commit with issue reference."""
        text = "feat: add feature\n\nCloses #123"
        found, has_issue = problems(text)
        assert found == []
        assert has_issue is True
