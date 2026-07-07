"""Regression tests for v0.3 adversarial-review findings."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from agentic_anything.ingest import classify_url, ingest_file
from agentic_anything.ingest_data import parse_feed

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_S_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


# ------------------------------------------------------------------ DOCX ---

def _docx(tmp_path: Path, body_xml: str, styles_xml: str = "") -> Path:
    doc = (f'<?xml version="1.0"?><w:document xmlns:w="{_W_NS}" '
           f'xmlns:mc="{_MC_NS}"><w:body>{body_xml}</w:body></w:document>')
    out = tmp_path / "t.docx"
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("word/document.xml", doc)
        if styles_xml:
            zf.writestr("word/styles.xml", styles_xml)
    return out


def test_docx_tabs_and_breaks_are_separators(tmp_path):
    body = ('<w:p><w:r><w:t>Name</w:t></w:r><w:r><w:tab/></w:r>'
            '<w:r><w:t>Alice</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>first line</w:t><w:br/><w:t>second line</w:t></w:r></w:p>')
    _, units = ingest_file(_docx(tmp_path, body))
    text = units[0].text()
    assert "Name Alice" in text
    assert "first line second line" in text


def test_docx_textbox_not_duplicated(tmp_path):
    body = (
        "<w:p><w:r>"
        "<mc:AlternateContent>"
        "<mc:Choice><w:drawing><w:txbxContent>"
        "<w:p><w:r><w:t>Box text once.</w:t></w:r></w:p>"
        "</w:txbxContent></w:drawing></mc:Choice>"
        "<mc:Fallback><w:pict><w:txbxContent>"
        "<w:p><w:r><w:t>Box text once.</w:t></w:r></w:p>"
        "</w:txbxContent></w:pict></mc:Fallback>"
        "</mc:AlternateContent>"
        "</w:r></w:p>"
        "<w:p><w:r><w:t>Body paragraph.</w:t></w:r></w:p>"
    )
    _, units = ingest_file(_docx(tmp_path, body))
    joined = " ".join(u.text() for u in units)
    assert joined.count("Box text once.") == 1
    assert "Body paragraph." in joined


def test_docx_table_rows_pipe_joined(tmp_path):
    body = (
        "<w:tbl>"
        "<w:tr><w:tc><w:p><w:r><w:t>City</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>Pop</w:t></w:r></w:p></w:tc></w:tr>"
        "<w:tr><w:tc><w:p><w:r><w:t>Paris</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>2161000</w:t></w:r></w:p></w:tc></w:tr>"
        "</w:tbl>"
    )
    _, units = ingest_file(_docx(tmp_path, body))
    text = units[0].text()
    assert "City | Pop" in text
    assert "Paris | 2161000" in text


def test_docx_localized_heading_styles(tmp_path):
    body = ('<w:p><w:pPr><w:pStyle w:val="berschrift1"/></w:pPr>'
            '<w:r><w:t>Einleitung</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Deutscher Text.</w:t></w:r></w:p>')
    styles = (f'<?xml version="1.0"?><w:styles xmlns:w="{_W_NS}">'
              '<w:style w:type="paragraph" w:styleId="berschrift1">'
              '<w:name w:val="heading 1"/></w:style></w:styles>')
    _, units = ingest_file(_docx(tmp_path, body, styles))
    assert any(u.title == "Einleitung" for u in units)


# ------------------------------------------------------------------ XLSX ---

def _xlsx(tmp_path: Path, sheet_xml: str, shared_xml: str = "",
          styles_xml: str = "") -> Path:
    out = tmp_path / "t.xlsx"
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("xl/workbook.xml",
                    f'<?xml version="1.0"?><workbook xmlns="{_S_NS}"><sheets>'
                    '<sheet name="S1" sheetId="1"/></sheets></workbook>')
        if shared_xml:
            zf.writestr("xl/sharedStrings.xml", shared_xml)
        if styles_xml:
            zf.writestr("xl/styles.xml", styles_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return out


def test_xlsx_rless_cells_sequential(tmp_path):
    sheet = (f'<?xml version="1.0"?><worksheet xmlns="{_S_NS}"><sheetData>'
             '<row><c t="inlineStr"><is><t>alpha</t></is></c><c><v>42</v></c></row>'
             "</sheetData></worksheet>")
    _, units = ingest_file(_xlsx(tmp_path, sheet))
    assert "alpha | 42" in units[0].text()


def test_xlsx_phonetic_rph_excluded(tmp_path):
    shared = (f'<?xml version="1.0"?><sst xmlns="{_S_NS}">'
              '<si><t>東京</t><rPh sb="0" eb="2"><t>トウキョウ</t></rPh></si></sst>')
    sheet = (f'<?xml version="1.0"?><worksheet xmlns="{_S_NS}"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c></row>'
             "</sheetData></worksheet>")
    _, units = ingest_file(_xlsx(tmp_path, sheet, shared))
    text = units[0].text()
    assert "東京" in text
    assert "トウキョウ" not in text


def test_xlsx_booleans_and_dates(tmp_path):
    styles = (f'<?xml version="1.0"?><styleSheet xmlns="{_S_NS}"><cellXfs count="2">'
              '<xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>')
    sheet = (f'<?xml version="1.0"?><worksheet xmlns="{_S_NS}"><sheetData>'
             '<row r="1"><c r="A1" s="1"><v>45123</v></c>'
             '<c r="B1" t="b"><v>1</v></c></row>'
             "</sheetData></worksheet>")
    _, units = ingest_file(_xlsx(tmp_path, sheet, styles_xml=styles))
    text = units[0].text()
    assert "2023-07-16" in text   # serial 45123 with date numFmt
    assert "TRUE" in text


# ------------------------------------------------------------- routing -----

def test_tld_extension_collision_still_crawls():
    assert classify_url("https://gov.md") == "crawl"
    assert classify_url("https://example.zip") == "crawl"
    assert classify_url("https://president.md") == "crawl"
    # with a real document path they are files again
    assert classify_url("https://gov.md/report.pdf") == "file"


def test_github_variants():
    assert classify_url("https://github.com/o/r#readme") == "repo"
    assert classify_url("https://github.com/o/r/tree/main/") == "repo"
    assert classify_url("https://github.com/o/r/blob/main/README.md") == "file"
    assert classify_url("https://github.com/o/r/issues/1") == "crawl"


def test_arxiv_variants():
    assert classify_url("https://arxiv.org/abs/hep-th/9901001") == "arxiv"
    assert classify_url("arxiv:hep-th/9901001") == "arxiv"
    assert classify_url("https://arxiv.org/abs/2401.12345?utm=x") == "arxiv"
    assert classify_url("https://arxiv.org/pdf/2401.12345.pdf") == "arxiv"


def test_video_url_fragment_and_port():
    assert classify_url("https://example.com/video.mp4#t=30") == "video"
    assert classify_url("https://youtube.com:443/watch?v=a") == "video"
    # lookalike domains still not treated as video hosts
    assert classify_url("https://myyoutube.com.evil.com/blog") == "crawl"


def test_feed_boundary():
    assert classify_url("https://x.com/notafeed.xml") == "crawl"
    assert classify_url("https://x.com/product-datafeed.xml") == "crawl"
    assert classify_url("https://x.com/feed.xml") == "feed"
    assert classify_url("https://x.com/morss") == "crawl"


def test_html_masquerading_as_pdf_rejected():
    from agentic_anything.fetcher import FetchResult
    from agentic_anything.ingest import IngestError, _check_downloaded_body

    html_result = FetchResult(url="u", final_url="u", status=200,
                              content_type="text/html",
                              body=b"<!DOCTYPE html><html>login</html>")
    with pytest.raises(IngestError, match="HTML page instead"):
        _check_downloaded_body("paper.pdf", html_result)
    pdf_result = FetchResult(url="u", final_url="u", status=200,
                             content_type="application/pdf",
                             body=b"%PDF-1.7 ...")
    _check_downloaded_body("paper.pdf", pdf_result)  # no raise


def test_localhost_gets_http_scheme():
    from agentic_anything.util import with_default_scheme

    assert with_default_scheme("localhost:8080").startswith("http://")
    assert with_default_scheme("127.0.0.1:8080/x").startswith("http://")
    assert with_default_scheme("example.com").startswith("https://")
    assert with_default_scheme("https://x.com") == "https://x.com"


# --------------------------------------------------------------- feeds -----

def test_rss1_rdf_feed():
    rdf = b"""<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns="http://purl.org/rss/1.0/"
             xmlns:dc="http://purl.org/dc/elements/1.1/">
      <channel rdf:about="https://x.com"><title>RDF Feed</title></channel>
      <item rdf:about="https://x.com/1"><title>Item One</title>
        <link>https://x.com/1</link><dc:date>2026-07-01</dc:date>
        <description>RDF item body.</description></item>
    </rdf:RDF>"""
    title, units = parse_feed(rdf, "https://x.com/rss")
    assert title == "RDF Feed"
    assert units[0].title == "Item One"
    assert "RDF item body." in units[0].text()


def test_rss2_content_encoded_preferred():
    rss = b"""<?xml version="1.0"?>
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel><title>T</title>
      <item><title>A</title><description>short teaser</description>
        <content:encoded>&lt;p&gt;Full rich body here.&lt;/p&gt;</content:encoded></item>
    </channel></rss>"""
    _, units = parse_feed(rss, "x")
    assert "Full rich body here." in units[0].text()


# ------------------------------------------------------------- archives ----

def test_tar_symlink_and_traversal_blocked(tmp_path):
    import io
    import tarfile

    from agentic_anything.ingest import _safe_extract_tar

    tar_path = tmp_path / "evil.tar"
    with tarfile.open(tar_path, "w") as tf:
        data = b"# ok\n\ncontent\n"
        info = tarfile.TarInfo("docs/ok.md")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
        link = tarfile.TarInfo("docs/link.md")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tf.addfile(link)
        trav = tarfile.TarInfo("../escape.md")
        trav.size = len(data)
        tf.addfile(trav, io.BytesIO(data))
    dest = tmp_path / "out"
    _safe_extract_tar(tar_path, dest)
    names = sorted(str(p.relative_to(dest)) for p in dest.rglob("*")
                   if p.is_file() or p.is_symlink())
    assert names == ["docs/ok.md"]
    assert not (tmp_path / "escape.md").exists()
