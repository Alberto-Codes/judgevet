"""Acceptance checks for offline documentation integrity."""

from pathlib import Path

from scripts import check_doc_links
from scripts.check_doc_links import check_links


def test_valid_links_and_code_literals(tmp_path: Path) -> None:
    (tmp_path / "target.md").write_text("# Target\n\n## Some `API`\n")
    page = tmp_path / "index.md"
    page.write_text(
        "[ok](target.md#some-api)\n\n[ref][destination]\n\n"
        "[destination]: target.md#target\n\n```text\n[not a link](missing.md)\n```\n"
    )
    assert check_links([page]) == []


def test_missing_file_reports_origin(tmp_path: Path) -> None:
    page = tmp_path / "index.md"
    page.write_text("[broken](absent.md)\n")
    findings = check_links([page])
    assert len(findings) == 1
    assert "index.md" in findings[0] and "absent.md" in findings[0]


def test_missing_fragment_in_reference_link(tmp_path: Path) -> None:
    page = tmp_path / "index.md"
    page.write_text("# Existing\n\n[broken][ref]\n\n[ref]: #absent\n")
    assert any("absent" in finding for finding in check_links([page]))


def test_image_target_and_encoded_path(tmp_path: Path) -> None:
    (tmp_path / "my file.md").write_text('# Hello\n<a id="custom"></a>\n')
    page = tmp_path / "index.md"
    page.write_text("[ok](my%20file.md#custom)\n\n![missing](image.png)\n")
    findings = check_links([page])
    assert len(findings) == 1 and "image.png" in findings[0]


def test_raw_html_and_remote_links(tmp_path: Path) -> None:
    page = tmp_path / "index.md"
    page.write_text(
        '<a id="part"></a><a href="#part">ok</a>\n'
        "[remote](https://example.invalid/no-network)\n"
        '<a href="missing.md">broken</a>\n'
    )
    findings = check_links([page])
    assert len(findings) == 1 and "missing.md" in findings[0]


def test_rendered_site_root_and_fragment(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text('<h1 id="home">Home</h1>')
    (tmp_path / "404.html").write_text('<a href="/#home">Home</a>')
    assert check_doc_links.check_site(tmp_path) == []


def test_rendered_site_broken_anchor(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text('<a href="#absent">Broken</a>')
    assert any("absent" in item for item in check_doc_links.check_site(tmp_path))
