"""Select exact documented CLI workflows and their complete input fixtures.

Examples:
    The isolated documentation gate calls prepare_cli after inventory validation.

See Also:
    - [judgevet.adapters.inbound.cli][]: CLI argument and output contract.
"""

import json
from pathlib import Path

from scripts.doc_example_inventory import Block, discover

WORKFLOWS = {
    "README.md": {3: "judgment", 4: "policy"},
    "docs/how-to/use-cli-files.md": {1: "judgment", 3: "state", 4: "judgment"},
    "docs/how-to/use-cli-policy.md": {3: "policy", 7: "automation"},
}


def source_block(
    pages: dict[str, list[Block]], page: str, number: int, language: str
) -> Block:
    """Select a block and reject stale language or position assumptions.

    Args:
        pages: Discovered source inventory.
        page: Required page.
        number: One-based block position.
        language: Required fence language.

    Returns:
        The exact inventoried block.

    Raises:
        ValueError: If the expected block is missing or has another language.
    """
    blocks = pages.get(page, [])
    if number > len(blocks) or blocks[number - 1].language != language:
        raise ValueError(f"{page}: expected {language} block {number}")
    return blocks[number - 1]


def prepare_cli(root: Path, workdir: Path) -> None:
    """Write exact scripts and JSON inputs to a child execution manifest.

    Args:
        root: Documentation root.
        workdir: Isolated execution directory.

    Raises:
        ValueError: If required documentation blocks are missing or changed.
    """
    pages = discover(root)
    policy_page = "docs/how-to/use-cli-policy.md"
    inputs = {
        "document.txt": "A short example.\n",
        "questions.json": source_block(pages, policy_page, 1, "json").text,
        "policy.json": source_block(pages, policy_page, 2, "json").text,
    }
    jobs = []
    for page, selections in WORKFLOWS.items():
        for number, kind in selections.items():
            block = source_block(pages, page, number, "bash")
            local_inputs = dict(inputs)
            if page == "docs/how-to/use-cli-files.md":
                local_inputs["questions.json"] = source_block(
                    pages, page, 2, "json"
                ).text
            jobs.append(
                {
                    "text": block.text,
                    "label": f"{page}:{block.line}",
                    "kind": kind,
                    "inputs": local_inputs,
                }
            )
    (workdir / "cli_examples.json").write_text(json.dumps(jobs))


def prepare_continuations(root: Path, workdir: Path) -> None:
    """Collect exact tutorial programs, commands and checkout script files.

    Args:
        root: Documentation and example source root.
        workdir: Isolated destination directory.

    Raises:
        ValueError: If a required source block is absent or has another language.
    """
    pages = discover(root)
    jobs = []
    for name, program_number, command_number in (
        ("first-judgment", 3, 4),
        ("first-policy", 1, 2),
    ):
        page = f"docs/tutorials/{name}.md"
        command = source_block(pages, page, command_number, "bash")
        expected = source_block(pages, page, command_number + 1, "text").text
        if name == "first-judgment":
            expected = (
                "Probability of billing: 0.85\n"
                "Resolved model: jev-1.13.0\nInput tokens: 10\n"
            )
        jobs.append(
            {
                "kind": "tutorial",
                "label": f"{page}:{command.line}",
                "command": command.text,
                "filename": name.replace("-", "_") + ".py",
                "program": source_block(pages, page, program_number, "python").text,
                "expected": expected,
            }
        )
    page = "docs/how-to/review-staged-diff.md"
    command = source_block(pages, page, 2, "bash")
    files = {
        name: (root / "examples/staged-review" / name).read_text()
        for name in ("review-staged.sh", "questions.json", "policy.json")
    }
    jobs.append(
        {
            "kind": "staged",
            "label": f"{page}:{command.line}",
            "command": command.text,
            "files": files,
        }
    )
    (workdir / "continuations.json").write_text(json.dumps(jobs))
