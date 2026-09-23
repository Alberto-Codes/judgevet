"""Enforce glossary vocabulary in declared prose and safe local-name contexts.

Examples:
    ```bash
    uv run python -m scripts.check_terminology
    ```

See Also:
    - [judgevet][]: Package whose terminology follows the glossary.
"""

import argparse
from pathlib import Path

from scripts.check_plain_english import scope
from scripts.prose_blocks import markdown_blocks, python_blocks
from scripts.terminology_identifiers import identifier_findings
from scripts.terminology_rules import Rule, read_rules, violations


def prose_findings(text: str, rules: list[Rule]) -> list[str]:
    """Check Markdown prose while preserving literal contracts.

    Args:
        text: Authored Markdown source.
        rules: Canonical glossary rows.

    Returns:
        Line-numbered preferred-wording diagnostics.
    """
    return [
        f"{line}: {finding}"
        for line, prose in markdown_blocks(text)
        for finding in violations(prose, rules)
    ]


def main() -> int:
    """Check the complete writing scope using its canonical glossary.

    Returns:
        Zero for clean terminology, one for findings or invalid inputs.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    findings = []
    try:
        rules = read_rules(args.root / "docs/reference/glossary.md")
        for path in scope(args.root):
            text = path.read_text()
            if path.suffix == ".py":
                found = [
                    f"{line}: {finding}"
                    for line, prose in python_blocks(text)
                    for finding in violations(prose, rules)
                ]
                found.extend(identifier_findings(text, rules))
            else:
                found = prose_findings(text, rules)
            findings.extend(f"{path}:{finding}" for finding in found)
    except (OSError, SyntaxError, ValueError) as error:
        print(f"Terminology: {error}")
        return 1
    for finding in findings:
        print(finding)
    print(f"Terminology: {len(findings)} findings; semantic review remains required")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
