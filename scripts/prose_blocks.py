"""Extract authored Markdown prose and package docstrings with source locations.

Examples:
    >>> markdown_blocks("Read `value` now.")
    [(1, 'Read   now.')]

See Also:
    - [judgevet][]: Package whose docstrings use this profile.
"""

import ast
import inspect
import re

from markdown_it import MarkdownIt

SECTIONS = {
    "Args:",
    "Arguments:",
    "Attributes:",
    "Returns:",
    "Raises:",
    "Yields:",
    "Examples:",
    "See Also:",
    "Notes:",
    "Note:",
    "Warnings:",
    "Warning:",
}
PARAMETER = re.compile(r"^\s+[\w.*]+(?:\s*\([^)]*\))?:\s+")
URL = re.compile(r"https?://\S+")


def markdown_blocks(text: str) -> list[tuple[int, str]]:
    """Extract visible inline prose with its containing block's starting line.

    Args:
        text: Markdown source, optionally with YAML frontmatter.

    Returns:
        Source line and prose pairs, including headings, lists and table cells.
    """
    lines = text.splitlines()
    if lines and lines[0] == "---":
        for index, line in enumerate(lines[1:], 1):
            if line == "---":
                lines[: index + 1] = [""] * (index + 1)
                break
    tokens = MarkdownIt("commonmark").enable("table").parse("\n".join(lines))
    blocks = []
    line_number = 1
    for token in tokens:
        if token.map:
            line_number = token.map[0] + 1
        if token.type != "inline":
            continue
        parts = []
        for child in token.children or []:
            if child.type == "text":
                parts.append(URL.sub(" ", child.content))
            elif child.type in {"softbreak", "hardbreak", "code_inline"}:
                parts.append(" ")
            elif child.type == "image":
                parts.append(child.content)
        prose = "".join(parts)
        if prose.strip():
            blocks.append((line_number, prose))
    return blocks


def section_prose(text: str) -> str:
    """Remove Google section syntax and doctests while retaining line positions.

    Args:
        text: Cleaned Python docstring content.

    Returns:
        Markdown-compatible prose with section descriptions retained.
    """
    lines = text.splitlines()
    section = ""
    doctest = False
    fenced = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            fenced = not fenced
        if fenced or stripped.startswith(("```", "~~~")):
            continue
        if stripped in SECTIONS:
            section = stripped
            doctest = False
            lines[index] = ""
        elif stripped.startswith(">>>") or (doctest and stripped):
            doctest = True
            lines[index] = ""
        elif not stripped:
            doctest = False
        elif section:
            lines[index] = PARAMETER.sub("- ", line).lstrip()
    return "\n".join(lines)


def python_blocks(source: str) -> list[tuple[int, str]]:
    """Extract module, class and function docstrings without reading code strings.

    Args:
        source: Python source text.

    Returns:
        Prose and absolute source line pairs for every docstring.

    Raises:
        SyntaxError: If the source does not parse as Python.
    """
    blocks = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        raw = ast.get_docstring(node, clean=False)
        if raw is None:
            continue
        first = node.body[0]
        # cleandoc removes leading empty lines; preserve their source offset.
        cleaned = inspect.cleandoc(raw)
        leading = len(raw.splitlines()) - len(raw.lstrip("\n").splitlines())
        for line, prose in markdown_blocks(section_prose(cleaned)):
            blocks.append((first.lineno + leading + line - 1, prose))
    return blocks
