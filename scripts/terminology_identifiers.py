"""Check annotated local names without changing public or wire vocabulary.

Examples:
    >>> list(local_annotations(__import__("ast").parse("value: int")))
    []

See Also:
    - [judgevet.domain.questions][]: Supported question annotations.
    - [judgevet.domain.answers][]: Supported individual answer annotations.
"""

import ast
from collections.abc import Iterator

from scripts.terminology_rules import Rule

QUESTION_TYPES = {"Question", "Noul", "Choice", "Score"}
ANSWER_TYPES = {"Answer", "NoulAnswer", "ChoiceAnswer", "ScoreAnswer"}


def local_annotations(
    node: ast.AST, in_function: bool = False
) -> Iterator[ast.AnnAssign]:
    """Select annotated locals, excluding module and class attributes.

    Args:
        node: Current syntax node.
        in_function: Whether this scope is a function body.

    Yields:
        Annotated assignments inside function scopes.
    """
    if isinstance(node, ast.ClassDef):
        in_function = False
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        in_function = True
    if in_function and isinstance(node, ast.AnnAssign):
        yield node
    for child in ast.iter_child_nodes(node):
        yield from local_annotations(child, in_function)


def imported_types(tree: ast.AST) -> dict[str, str]:
    """Resolve direct imports of the supported judgevet type vocabulary.

    Args:
        tree: Parsed source module.

    Returns:
        Local import names mapped to glossary context selectors.
    """
    types = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level:
            continue
        if node.module not in {
            "judgevet",
            "judgevet.domain.questions",
            "judgevet.domain.answers",
        }:
            continue
        for alias in node.names:
            if alias.name in QUESTION_TYPES:
                types[alias.asname or alias.name] = "question"
            elif alias.name in ANSWER_TYPES:
                types[alias.asname or alias.name] = "answer"
    return types


def identifier_findings(source: str, rules: list[Rule]) -> list[str]:
    """Check exact underscore-delimited words in directly annotated local names.

    Args:
        source: Python source.
        rules: Canonical glossary rows.

    Returns:
        Source-line diagnostics with preferred wording.

    Raises:
        SyntaxError: If source is not valid Python.
    """
    tree = ast.parse(source)
    types = imported_types(tree)
    findings = []
    for node in local_annotations(tree):
        if not isinstance(node.target, ast.Name) or not isinstance(
            node.annotation, ast.Name
        ):
            continue
        mode = types.get(node.annotation.id)
        for rule in rules:
            if rule.mode == mode:
                findings.extend(
                    f"{node.lineno}: local '{node.target.id}': "
                    f"use '{rule.preferred}' instead of '{term}'"
                    for term in rule.avoided
                    if term in node.target.id.split("_")
                )
    return findings
