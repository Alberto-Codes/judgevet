"""Read glossary terms and apply explicitly bounded lexical contexts.

Examples:
    >>> plural("query")
    'queries'

See Also:
    - [judgevet.domain.questions][]: Question type vocabulary.
"""

import re
from dataclasses import dataclass
from pathlib import Path

COLUMNS = ("Preferred", "Avoid", "Context", "Check")

CONTEXTS = {
    "question": (r"Jev|evaluation|judgment", r"to Jev|for Jev"),
    "answer": (
        r"Noul|Choice|Score|named question|individual question|per-question",
        r"for (?:a|one|each) (?:named )?question",
    ),
    "confidence": (r"Choice|Score|model", r"of (?:the )?(?:Choice|Score)"),
    "boundary": (r"judgevet|typed|SystemOnePort|AsyncSystemOnePort", ""),
    "adapter": (r"HTTP|CLI|MCP|SystemOnePort|AsyncSystemOnePort|judgevet", ""),
    "always": ("", ""),
    "human": ("", ""),
}


@dataclass(frozen=True)
class Rule:
    """A canonical glossary row with a declared detection context.

    Attributes:
        preferred: Wording suggested by the glossary.
        avoided: Exact avoided terms from the same row.
        mode: Named lexical context or human-review requirement.
    """

    preferred: str
    avoided: tuple[str, ...]
    mode: str


def read_rules(path: Path) -> list[Rule]:
    """Read the glossary's structured canonical vocabulary table.

    Args:
        path: Canonical glossary Markdown.

    Returns:
        Validated rows with a single source for preferred and avoided terms.

    Raises:
        ValueError: If the table is missing, empty or malformed.
        OSError: If the glossary cannot be read.
    """
    rows = []
    active = False
    for line in path.read_text().splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if tuple(cells) == COLUMNS:
            active = True
            continue
        if not active:
            continue
        if not line.startswith("|"):
            break
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        if len(cells) != len(COLUMNS) or cells[-1] not in CONTEXTS or not all(cells):
            raise ValueError("malformed canonical vocabulary row")
        terms = tuple(term.strip().strip("`") for term in cells[1].split(";"))
        rows.append(Rule(cells[0], terms, cells[-1]))
    if not rows:
        raise ValueError("canonical vocabulary table is missing or empty")
    return rows


def plural(term: str) -> str:
    """Return the simple plural used by the declared lexical profile.

    Args:
        term: A glossary term.

    Returns:
        A form ending in s, or ies for a final y.
    """
    return term[:-1] + "ies" if term.endswith("y") else term + "s"


def violations(prose: str, rules: list[Rule]) -> list[str]:
    """Find terms in explicit contexts without classifying ambiguous prose.

    Args:
        prose: Structurally extracted authored prose.
        rules: Canonical glossary rows.

    Returns:
        Preferred-wording diagnostics for recognized contexts.
    """
    findings = []
    for rule in rules:
        if rule.mode == "human":
            continue
        before, after = CONTEXTS[rule.mode]
        for term in rule.avoided:
            word = rf"\b(?:{re.escape(term)}|{re.escape(plural(term))})\b"
            contexts = [word] if rule.mode == "always" else []
            if before:
                contexts.append(rf"\b(?:{before})\s+{word}")
            if after:
                contexts.append(rf"{word}\s+(?:{after})\b")
            if any(re.search(pattern, prose, re.IGNORECASE) for pattern in contexts):
                findings.append(
                    f"use '{rule.preferred}' instead of '{term}' ({rule.mode} context)"
                )
    return findings
