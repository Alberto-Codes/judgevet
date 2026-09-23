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


def test_repository_url_resolves_offline(tmp_path: Path) -> None:
    page = tmp_path / "README.md"
    (tmp_path / "target.md").write_text("# Target\n")
    page.write_text(
        "[read](https://github.com/Alberto-Codes/judgevet/blob/main/target.md#target)\n"
    )
    assert check_links([page], repository_root=tmp_path) == []


def test_repository_url_missing_file_fails(tmp_path: Path) -> None:
    page = tmp_path / "README.md"
    page.write_text(
        "[read](https://github.com/Alberto-Codes/judgevet/blob/main/missing.md)\n"
    )
    findings = check_links([page], repository_root=tmp_path)
    assert len(findings) == 1
    assert "missing target" in findings[0]


def test_repository_url_missing_anchor_fails(tmp_path: Path) -> None:
    page = tmp_path / "README.md"
    (tmp_path / "target.md").write_text("# Target\n")
    page.write_text(
        "[read](https://github.com/Alberto-Codes/judgevet/blob/main/target.md#absent)\n"
    )
    findings = check_links([page], repository_root=tmp_path)
    assert len(findings) == 1
    assert "missing anchor" in findings[0]


def test_project_site_prefix_resolves_assets_and_anchors(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text('<h1 id="home">Home</h1>')
    (tmp_path / "style.css").write_text("body {}")
    (tmp_path / "404.html").write_text(
        '<a href="/judgevet/#home">Home</a><img src="/judgevet/style.css">'
    )
    assert check_doc_links.check_site(tmp_path, site_path="/judgevet/") == []


def test_project_site_prefix_preserves_missing_targets(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<a href="/judgevet/missing/">Missing</a>'
        '<a href="/judgevet/#absent">Absent</a>'
        '<a href="/elsewhere/">Outside</a>'
    )
    findings = check_doc_links.check_site(tmp_path, site_path="/judgevet/")
    assert len(findings) == 3
    assert any("missing rendered anchor" in item for item in findings)
    assert sum("missing rendered target" in item for item in findings) == 2


def test_published_site_links_resolve_offline(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.md").write_text("# Home\n")
    (docs / "guide.md").write_text("# Guide\n")
    section = docs / "section"
    section.mkdir()
    (section / "index.md").write_text("# Section\n")
    page = tmp_path / "README.md"
    page.write_text(
        "[home](https://alberto-codes.github.io/judgevet/#home)\n"
        "[guide](https://alberto-codes.github.io/judgevet/guide/#guide)\n"
        "[section](https://alberto-codes.github.io/judgevet/section/#section)\n"
    )
    assert check_links([page], repository_root=tmp_path) == []


def test_published_site_missing_targets_and_anchors_fail(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n")
    page = tmp_path / "README.md"
    page.write_text(
        "[missing](https://alberto-codes.github.io/judgevet/missing/)\n"
        "[anchor](https://alberto-codes.github.io/judgevet/guide/#absent)\n"
    )
    findings = check_links([page], repository_root=tmp_path)
    assert len(findings) == 2
    assert "missing target" in findings[0]
    assert "missing anchor" in findings[1]
