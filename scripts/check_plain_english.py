"""Enforce the declared local prose profile, without claiming STE compliance.

Examples:
    Run the complete declared documentation scope:

    ```bash
    uv run python -m scripts.check_plain_english
    ```

See Also:
    - [judgevet][]: Package whose docstrings are checked.
"""

import argparse
import re
from pathlib import Path

from scripts.prose_blocks import markdown_blocks, python_blocks

LIMIT = 25
BANNED = re.compile(
    r"\b(?:seamless|robust|powerful|blazing|cutting-edge)\b", re.IGNORECASE
)
ABBREVIATION = re.compile(
    r"\b(?:e\.g\.|i\.e\.|etc\.|vs\.|Dr\.|Mr\.|Mrs\.)", re.IGNORECASE
)
WORDS = re.compile(r"[A-Za-z0-9]+(?:['\u2019.-][A-Za-z0-9]+)*")


def findings_for(path: Path) -> list[str]:
    """Check a Markdown file or Python file's docstrings.

    Args:
        path: Authored source file.

    Returns:
        Actionable file, block-start line and rule diagnostics.

    Raises:
        OSError: If the source cannot be read.
        SyntaxError: If a Python file cannot be parsed.
    """
    text = path.read_text()
    blocks = python_blocks(text) if path.suffix == ".py" else markdown_blocks(text)
    findings = []
    for line, prose in blocks:
        findings.extend(
            f"{path}:{line}: marketing adjective '{match.group()}'; "
            "describe the specific behavior"
            for match in BANNED.finditer(prose)
        )
        protected = ABBREVIATION.sub(lambda m: m.group().replace(".", "~"), prose)
        for sentence in re.split(r"[.!?](?:\s+|$)", protected):
            count = len(WORDS.findall(sentence.replace("~", ".")))
            if count > LIMIT:
                findings.append(
                    f"{path}:{line}: {count} words exceeds {LIMIT}; "
                    f"split this sentence: {sentence.replace('~', '.').strip()}"
                )
    return findings


def scope(root: Path) -> list[Path]:
    """Select the complete declared authored-documentation scope.

    Args:
        root: Repository directory.

    Returns:
        README, SECURITY, all docs Markdown and all package Python sources.
    """
    return [
        root / "README.md",
        root / "SECURITY.md",
        *sorted((root / "docs").rglob("*.md")),
        *sorted((root / "src/judgevet").rglob("*.py")),
    ]


def main() -> int:
    """Check every scoped file and fail for findings or unreadable source.

    Returns:
        Zero for clean prose, one for findings or invalid input.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    findings = []
    try:
        for path in scope(args.root):
            findings.extend(findings_for(path))
    except (OSError, SyntaxError) as error:
        print(f"Plain English: {error}")
        return 1
    for finding in findings:
        print(finding)
    print(
        f"Plain English: {len(findings)} findings (local profile, not STE compliance)"
    )
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
