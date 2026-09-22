"""Command-line input resolution before adapter construction.

Examples:
    ```python
    from judgevet.adapters.inbound.cli_inputs import InputFailure

    assert InputFailure("Invalid source", code=2).code == 2
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Console composition root.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Type alias for the parse function signature
ParseFunc = Callable[[str], dict[str, Any]]
InputTuple = tuple[str, str]


class InputFailure(ValueError):
    """Report a sanitized input failure with its process status.

    Attributes:
        code (int): Process status; 1 for content errors and 2 for source usage.

    Examples:
        ```python
        failure = InputFailure("Invalid source", code=2)
        assert failure.code == 2
        ```
    """

    def __init__(self, message: str, code: int = 1) -> None:
        """Initialize input failure exception.

        Args:
            message: Sanitized diagnostic for the selected source.
            code: Exit status, defaulting to content error 1.
        """
        super().__init__(message)
        self.code = code


def _validate_selection_conflicts(
    state: str | None,
    questions: str | None,
    state_files: list[str],
    question_files: list[str],
) -> None:
    """Validate that input selection is not ambiguous or conflicting.

    Args:
        state: Positional state argument (None if not provided).
        questions: Positional questions argument (None if not provided).
        state_files: List of --state-file arguments.
        question_files: List of --questions-file arguments.

    Raises:
        InputFailure: If selection conflicts (e.g., both positional and file specified).
    """
    # Check for repeated state sources
    if len(state_files) > 1:
        raise InputFailure("Multiple --state-file options are not allowed", code=2)

    # Check for repeated question sources
    if len(question_files) > 1:
        raise InputFailure("Multiple --questions-file options are not allowed", code=2)

    # Check for conflicting sources
    if state is not None and state_files:
        raise InputFailure(
            "Positional STATE conflicts with --state-file option", code=2
        )

    if questions is not None and question_files:
        raise InputFailure(
            "Positional QUESTIONS conflicts with --questions-file option", code=2
        )

    # Check that at least one state source is provided
    if state is None and not state_files:
        raise InputFailure("No state source provided", code=2)

    # Check that at least one question source is provided
    if questions is None and not question_files:
        raise InputFailure("No question source provided", code=2)


def _read_state_content(source: str) -> str:
    """Read state content from file or stdin.

    Args:
        source: Source identifier: "-" for stdin, otherwise a file path.

    Returns:
        UTF-8 decoded content.

    Raises:
        InputFailure: If reading fails with appropriate category diagnostic.
    """
    try:
        if source == "-":
            content = sys.stdin.buffer.read().decode("utf-8")
        else:
            content = Path(source).read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        source_cat = "stdin" if source == "-" else "--state-file"
        raise InputFailure(f"{source_cat}: read or decode error", code=1) from None

    # Reject whitespace-only content
    if content.strip() == "":
        source_cat = "stdin" if source == "-" else "--state-file"
        raise InputFailure(f"{source_cat}: content is empty or whitespace-only", code=1)

    return content


def _validate_state_content(content: str) -> str:
    """Validate state content and return original.

    Args:
        content: Raw state content to validate.

    Returns:
        Original content unchanged.

    Raises:
        InputFailure: If content is invalid JSON when it appears to be JSON.
    """
    # Only parse JSON if content starts with [ or {
    if content and content[0] in ("[", "{"):
        try:
            json.loads(content)
        except json.JSONDecodeError:
            raise InputFailure("state: invalid JSON", code=1) from None

    # Preserve original content including newlines
    return content


def _load_state(state_files: list[str] | None, state: str | None) -> str:
    """Load state from file/stdin if specified, otherwise use positional.

    Args:
        state_files: List of state file sources (from --state-file).
        state: Positional state argument.

    Returns:
        Loaded state content.

    Raises:
        InputFailure: If reading or content validation fails.
    """
    if state_files:
        return _validate_state_content(_read_state_content(state_files[0]))
    if state is None:
        raise InputFailure("No state source provided", code=2)
    return state


def _read_question_file(path: str) -> str:
    """Read question file content with UTF-8 validation.

    Args:
        path: Path to the question file.

    Returns:
        UTF-8 decoded content.

    Raises:
        InputFailure: If file cannot be read.
    """
    file_path = Path(path)

    # Read content
    try:
        content = file_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        raise InputFailure("--questions-file: read or decode error", code=1) from None

    # Reject empty/whitespace content
    if content.strip() == "":
        raise InputFailure("--questions-file: empty or whitespace-only", code=1)

    return content


def _validate_question_file_content(content: str) -> str:
    """Validate question file JSON content.

    Args:
        content: Raw question file content.

    Returns:
        Original content if valid.

    Raises:
        InputFailure: If content is invalid.
    """
    # Parse JSON with duplicate key detection
    try:
        data = json.loads(content, object_pairs_hook=_check_duplicate_keys)
    except json.JSONDecodeError:
        raise InputFailure("--questions-file: invalid JSON", code=1) from None

    # Must be an object (dict)
    if not isinstance(data, dict):
        raise InputFailure("--questions-file: root must be JSON object", code=1)

    # Must be non-empty
    if not data:
        raise InputFailure("--questions-file: empty question object", code=1)

    # Validate each question entry
    valid_types = {"noul", "choice", "score"}
    for name, entry in data.items():
        # Name must be non-empty string
        if not isinstance(name, str) or name == "":
            raise InputFailure(
                "--questions-file: question name must be non-empty string", code=1
            )

        # Entry must be a dict
        if not isinstance(entry, dict):
            raise InputFailure(
                "--questions-file: question entry must be a JSON object", code=1
            )

        qtype = entry.get("type")
        if not isinstance(qtype, str) or qtype not in valid_types:
            raise InputFailure("--questions-file: invalid question type")

    return content


def _check_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Check for duplicate keys in JSON object pairs.

    Args:
        pairs: Key-value pairs from JSON parsing.

    Returns:
        Pairs as dictionary.

    Raises:
        InputFailure: If duplicate keys are found.
    """
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise InputFailure("--questions-file: duplicate key in JSON object", code=1)
        seen.add(key)
    return dict(pairs)


def _parse_questions(content: str, parse: ParseFunc) -> str:
    """Parse and validate questions using injected parse function.

    Args:
        content: Raw question content.
        parse: Domain parse function (from cli.parse_questions).

    Returns:
        Original content if parsing succeeds.

    Raises:
        InputFailure: If domain parsing fails.
    """
    try:
        parse(content)
    except (ValueError, TypeError, KeyError, AttributeError):
        raise InputFailure("--questions-file: invalid question data", code=1) from None

    return content


def resolve_inputs(
    state: str | None,
    questions: str | None,
    state_files: list[str],
    question_files: list[str],
    parse: ParseFunc,
) -> InputTuple:
    """Resolve and validate all input sources.

    Args:
        state: Positional state argument.
        questions: Positional questions argument.
        state_files: List of --state-file arguments.
        question_files: List of --questions-file arguments.
        parse: Domain parse function for questions.

    Returns:
        Resolved (state_string, questions_string).

    Raises:
        InputFailure: If input selection is invalid or content cannot be read/validated.
    """
    # Validate all selection conflicts first (before any file reads)
    _validate_selection_conflicts(state, questions, state_files, question_files)

    # Load state (from file/stdin if specified, else positional)
    resolved_state = _load_state(state_files, state)

    # Load and validate questions
    if question_files:
        question_content = _read_question_file(question_files[0])
        resolved_questions = _validate_question_file_content(question_content)
        resolved_questions = _parse_questions(resolved_questions, parse)
    else:
        if questions is None:
            raise InputFailure("No question source provided", code=2)
        resolved_questions = questions

    return resolved_state, resolved_questions
