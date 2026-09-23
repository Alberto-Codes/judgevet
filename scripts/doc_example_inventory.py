"""Require explicit classifications for every README and user-doc fence.

Examples:
    Run ``uv run python -m scripts.doc_example_inventory`` from the checkout.

See Also:
    - [judgevet][]: Package described by the inventoried examples.
"""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

KINDS = frozenset({"runnable", "continuation", "template", "output"})


@dataclass(frozen=True)
class Block:
    """One fence with its exact body and source location.

    Attributes:
        language: Fence language, or text for an unlabelled fence.
        text: Exact body, including original newlines.
        line: One-based opening fence line.
    """

    language: str
    text: str
    line: int


def extract_blocks(text: str, page: str) -> list[Block]:
    """Extract backtick and tilde fences without rewriting their bodies.

    Args:
        text: Markdown source.
        page: Diagnostic page name.

    Returns:
        Blocks in document order.

    Raises:
        ValueError: If a fence has no matching close.
    """
    lines = text.splitlines(keepends=True)
    blocks = []
    index = 0
    while index < len(lines):
        match = re.fullmatch(r" {0,3}(`{3,}|~{3,})([^\n]*)\n?", lines[index])
        if match is None:
            index += 1
            continue
        fence, info = match.groups()
        start = index
        index += 1
        closing = re.compile(r" {0,3}" + fence[0] + "{" + str(len(fence)) + r",}\s*")
        while index < len(lines) and closing.fullmatch(lines[index]) is None:
            index += 1
        if index == len(lines):
            raise ValueError(f"{page}:{start + 1}: unclosed fence")
        language = info.strip().split()[0] if info.strip() else "text"
        blocks.append(Block(language, "".join(lines[start + 1 : index]), start + 1))
        index += 1
    return blocks


def discover(root: Path) -> dict[str, list[Block]]:
    """Inventory README and authored docs outside the maintainer directory.

    Args:
        root: Repository root.

    Returns:
        Relative page paths mapped to their nonempty block lists.

    Raises:
        ValueError: If a fence is unclosed.
    """
    paths = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    result = {}
    for path in paths:
        relative = path.relative_to(root)
        if relative.parts[:2] == ("docs", "maintainers"):
            continue
        blocks = extract_blocks(path.read_text(), relative.as_posix())
        if blocks:
            result[relative.as_posix()] = blocks
    return result


def validate(root: Path, manifest: Path) -> int:
    """Compare current fences with explicit language, kind and reason records.

    Args:
        root: Repository root to inspect.
        manifest: JSON classification file.

    Returns:
        Number of classified blocks.

    Raises:
        ValueError: If classification is incomplete, stale or malformed.
    """
    pages = discover(root)
    records = json.loads(manifest.read_text())
    if not pages or not isinstance(records, dict) or not records:
        raise ValueError("unexpectedly empty example inventory")
    if pages.keys() != records.keys():
        missing = sorted(pages.keys() - records.keys())
        stale = sorted(records.keys() - pages.keys())
        raise ValueError(f"page mismatch: unclassified={missing}, stale={stale}")
    for page, blocks in pages.items():
        entries = records[page]
        if not isinstance(entries, list) or len(entries) != len(blocks):
            raise ValueError(f"{page}: block count differs from classification")
        for number, (block, entry) in enumerate(zip(blocks, entries, strict=True), 1):
            check_entry(entry, block, f"{page}:{block.line} block {number}")
    return sum(map(len, pages.values()))


def check_entry(entry: object, block: Block, location: str) -> None:
    """Check one classification without executing its example.

    Args:
        entry: JSON record to validate.
        block: Actual fenced block.
        location: Page and block diagnostic prefix.

    Raises:
        ValueError: If the record lacks a valid language, kind or reason.
    """
    if not isinstance(entry, dict) or set(entry) != {"language", "kind", "reason"}:
        raise ValueError(f"{location}: expected language, kind and reason")
    if entry["language"] != block.language:
        raise ValueError(f"{location}: language differs from classification")
    if not isinstance(entry["kind"], str) or entry["kind"] not in KINDS:
        raise ValueError(f"{location}: unknown classification kind")
    if not isinstance(entry["reason"], str) or not entry["reason"].strip():
        raise ValueError(f"{location}: classification requires a reason")


def main() -> int:
    """Run inventory validation with page/block diagnostics.

    Returns:
        Zero for a complete inventory, one for a finding.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--manifest", type=Path, default=Path("scripts/doc_examples.json")
    )
    args = parser.parse_args()
    try:
        count = validate(args.root, args.manifest)
    except (OSError, ValueError) as error:
        print(f"Example inventory: {error}")
        return 1
    print(
        f"Example inventory: {count} classified blocks; execution is a separate check"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
