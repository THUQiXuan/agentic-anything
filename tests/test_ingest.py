"""Ingestion of non-web resources (documents, books, transcripts, folders)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from agentic_anything.ingest import (
    IngestError,
    build_pack_from_source,
    detect_source_kind,
    ingest_file,
)
from agentic_anything.query import PackReader, search_pack
from agentic_anything.util import read_json

RESOURCES = Path(__file__).parent / "fixtures" / "resources"


def test_detect_source_kind(tmp_path):
    assert detect_source_kind("https://example.com/x") == "web"
    assert detect_source_kind("example.com") == "web"
    file_path = tmp_path / "a.txt"
    file_path.write_text("hi")
    assert detect_source_kind(str(file_path)) == "file"
    assert detect_source_kind(str(tmp_path)) == "dir"
    with pytest.raises(IngestError):
        detect_source_kind("/no/such/path/anywhere")


def test_markdown_sections():
    rtype, units = ingest_file(RESOURCES / "handbook.md")
    assert rtype == "document"
    titles = [u.title for u in units]
    assert "Pricing Model" in titles
    pricing = next(u for u in units if u.title == "Pricing Model")
    assert "$79 per month" in pricing.text()
    assert pricing.kind == "section"
    assert all(u.unit_id for u in units)
    assert len({u.unit_id for u in units}) == len(units)


def test_text_chunks():
    rtype, units = ingest_file(RESOURCES / "story.txt")
    assert rtype == "document"
    assert units, "text file must produce at least one unit"
    joined = " ".join(u.text() for u in units)
    assert "Master Sprocket" in joined
    assert "measure twice, spin once" in joined


def test_subtitles_time_windows():
    rtype, units = ingest_file(RESOURCES / "lecture.srt")
    assert rtype == "video"
    assert len(units) >= 2  # cues span >6 minutes; 3-minute windows
    first = units[0]
    assert first.kind == "segment"
    assert first.meta["start_seconds"] == pytest.approx(1.0)
    assert "widget engineering lecture" in first.text()
    assert "–" in first.locator  # time-range locator
    last = units[-1]
    assert "E42" in last.text()


def _make_epub(path: Path) -> Path:
    """Minimal two-chapter EPUB assembled with stdlib zipfile."""
    epub = path / "tiny.epub"
    with zipfile.ZipFile(epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0"?>
            <package xmlns="http://www.idpf.org/2007/opf" version="2.0">
              <manifest>
                <item id="c1" href="chap1.xhtml" media-type="application/xhtml+xml"/>
                <item id="c2" href="chap2.xhtml" media-type="application/xhtml+xml"/>
              </manifest>
              <spine><itemref idref="c2"/><itemref idref="c1"/></spine>
            </package>""",
        )
        zf.writestr(
            "OEBPS/chap1.xhtml",
            "<html><head><title>The Beginning</title></head><body>"
            "<h1>The Beginning</h1>"
            + "".join(f"<p>Opening paragraph {i} about the humble widget.</p>" for i in range(12))
            + "</body></html>",
        )
        zf.writestr(
            "OEBPS/chap2.xhtml",
            "<html><head><title>The Reveal</title></head><body>"
            "<h1>The Reveal</h1>"
            + "".join(f"<p>Revelation paragraph {i}: the spindle was gold.</p>" for i in range(12))
            + "</body></html>",
        )
    return epub


def test_epub_chapters_spine_order(tmp_path):
    epub = _make_epub(tmp_path)
    rtype, units = ingest_file(epub)
    assert rtype == "book"
    assert len(units) == 2
    # spine says chap2 first
    assert units[0].title == "The Reveal"
    assert units[1].title == "The Beginning"
    assert units[0].kind == "chapter"
    assert "spindle was gold" in units[0].text()


def test_epub_bad_zip(tmp_path):
    fake = tmp_path / "broken.epub"
    fake.write_bytes(b"this is not a zip at all")
    with pytest.raises(IngestError, match="bad zip"):
        ingest_file(fake)


def test_unsupported_extension(tmp_path):
    weird = tmp_path / "data.xyz"
    weird.write_text("hello")
    with pytest.raises(IngestError, match="unsupported file type"):
        ingest_file(weird)


def test_directory_collection(tmp_path):
    src = tmp_path / "library"
    (src / "sub").mkdir(parents=True)
    (src / "notes.md").write_text("# Notes\n\nWidget notes here.\n")
    (src / "sub" / "extra.txt").write_text("Extra fact: gears mesh at dawn.\n")
    (src / "ignored.bin").write_bytes(b"\x00\x01")
    result = build_pack_from_source(str(src), tmp_path / "pack")
    assert result.page_count >= 2
    site = read_json(tmp_path / "pack" / "site.json")
    assert site["resource_type"] == "collection"
    all_text = ""
    for page in site["pages"]:
        all_text += (tmp_path / "pack" / "pages" / f"{page['page_id']}.md").read_text(
            encoding="utf-8"
        )
    assert "gears mesh at dawn" in all_text
    assert "Widget notes" in all_text


def test_ingested_pack_full_stack(tmp_path):
    """An ingested pack must work with PackReader, search, skill and clify."""
    result = build_pack_from_source(str(RESOURCES / "handbook.md"), tmp_path / "pack",
                                    site_id="handbook")
    assert result.page_count >= 4

    reader = PackReader(tmp_path / "pack")
    info = reader.info()
    assert info["site_id"] == "handbook"

    discovery = read_json(tmp_path / "pack" / "agent-pack.json")
    assert discovery["resource_type"] == "document"

    hits = search_pack(reader, "team tier price per month", top=3)
    assert hits and "pricing" in hits[0]["page_id"]

    # deterministic skill + site cli generate fine on non-web packs
    from agentic_anything.skills import generate_skill
    from agentic_anything.sitecli import generate_site_cli

    skill_path = generate_skill(tmp_path / "pack", llm_config=None, use_llm=False)
    assert "handbook" in skill_path.read_text(encoding="utf-8")
    cli_path = generate_site_cli(tmp_path / "pack")
    assert cli_path.exists()


def test_srt_pack_end_to_end(tmp_path):
    result = build_pack_from_source(str(RESOURCES / "lecture.srt"), tmp_path / "pack")
    reader = PackReader(tmp_path / "pack")
    assert reader.site["resource_type"] == "video"
    hits = search_pack(reader, "error code E42 cache", top=2)
    assert hits
    manifest = reader.page(hits[0]["page_id"])
    assert manifest["provenance"]["capture_mode"] == "ingest"
    assert "start_seconds" in manifest["provenance"]
