"""Strict source-reference acceptance using an isolated documentation tree."""

from pathlib import Path

import pytest
from mkdocs.commands.build import build
from mkdocs.config import load_config
from mkdocs.exceptions import Abort


def make_config(tmp_path: Path, symbol: str) -> Path:
    """Create an isolated source-reference build configuration."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text(
        f"# API\n\n[Question][{symbol}]\n\n"
        + "\n\n".join(
            f"::: judgevet.domain.{name}"
            for name in ("questions", "answers", "response", "usage")
        )
    )
    source = Path("src").resolve()
    config = tmp_path / "mkdocs.yml"
    config.write_text(
        f"site_name: Test\nplugins:\n  - mkdocstrings:\n"
        f"      handlers:\n        python:\n          paths: ['{source}']\n"
    )
    return config


def test_strict_reference_resolves(tmp_path: Path) -> None:
    config = make_config(tmp_path, "judgevet.domain.questions.Noul")
    build(load_config(config_file=str(config), strict=True))
    html = (tmp_path / "site/index.html").read_text()
    assert 'id="judgevet.domain.questions.Noul"' in html
    assert 'href="#judgevet.domain.questions.Noul"' in html


def test_strict_reference_rejects_unknown_symbol(tmp_path: Path) -> None:
    config = make_config(tmp_path, "judgevet.domain.questions.MissingQuestion")
    with pytest.raises(Abort, match="warning"):
        build(load_config(config_file=str(config), strict=True))
