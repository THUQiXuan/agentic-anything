"""v0.3 ingestion coverage: office, data, sqlite, email, archives, repos,
CLI software, media (with stubbed external tools), URL classification."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import zipfile
from pathlib import Path

import pytest

from agentic_anything.ingest import (
    IngestError,
    build_pack_from_cli_tool,
    build_pack_from_source,
    classify_url,
    ingest_file,
)
from agentic_anything.query import PackReader, search_pack

_S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


# ----------------------------------------------------------------- office --

def _make_docx(path: Path) -> Path:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    doc = f"""<?xml version="1.0"?>
    <w:document xmlns:w="{w}"><w:body>
      <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
        <w:r><w:t>Quarterly Report</w:t></w:r></w:p>
      <w:p><w:r><w:t>Revenue grew by </w:t></w:r><w:r><w:t>42 percent</w:t></w:r></w:p>
      <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
        <w:r><w:t>Risks</w:t></w:r></w:p>
      <w:p><w:r><w:t>Widget shortages remain the top risk.</w:t></w:r></w:p>
    </w:body></w:document>"""
    out = path / "report.docx"
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", doc)
    return out


def test_docx(tmp_path):
    rtype, units = ingest_file(_make_docx(tmp_path))
    assert rtype == "document"
    titles = [u.title for u in units]
    assert "Quarterly Report" in titles and "Risks" in titles
    joined = " ".join(u.text() for u in units)
    assert "Revenue grew by 42 percent" in joined  # runs joined correctly
    assert "Widget shortages" in joined


def test_pptx(tmp_path):
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    def slide(*lines):
        paras = "".join(
            f"<a:p><a:r><a:t>{ln}</a:t></a:r></a:p>" for ln in lines)
        return (f'<?xml version="1.0"?><p:sld xmlns:p="x" xmlns:a="{a}">'
                f"<p:cSld>{paras}</p:cSld></p:sld>")
    out = tmp_path / "deck.pptx"
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("ppt/slides/slide1.xml", slide("Vision 2030", "Widgets everywhere"))
        zf.writestr("ppt/slides/slide2.xml", slide("Roadmap", "Q1: spin faster"))
    rtype, units = ingest_file(out)
    assert rtype == "presentation"
    assert len(units) == 2
    assert units[0].title.startswith("Slide 1: Vision 2030")
    assert "spin faster" in units[1].text()


def test_xlsx(tmp_path):
    shared = (f'<?xml version="1.0"?><sst xmlns="{_S}">'
              "<si><t>city</t></si><si><t>Paris</t></si><si><t>Tokyo</t></si></sst>")
    sheet = (f'<?xml version="1.0"?><worksheet xmlns="{_S}"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1"><v>100</v></c></row>'
             '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><v>2161</v></c></row>'
             '<row r="3"><c r="A3" t="s"><v>2</v></c><c r="B3"><v>1396</v></c></row>'
             "</sheetData></worksheet>")
    workbook = (f'<?xml version="1.0"?><workbook xmlns="{_S}"><sheets>'
                '<sheet name="Cities" sheetId="1"/></sheets></workbook>')
    out = tmp_path / "cities.xlsx"
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/sharedStrings.xml", shared)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    rtype, units = ingest_file(out)
    assert rtype == "dataset"
    assert units[0].title == "Sheet: Cities"
    text = units[0].text()
    assert "Paris | 2161" in text and "Tokyo | 1396" in text


# ------------------------------------------------------------------- data --

def test_csv(tmp_path):
    f = tmp_path / "pop.csv"
    f.write_text("city,population\nParis,2161000\nTokyo,13960000\n", encoding="utf-8")
    rtype, units = ingest_file(f)
    assert rtype == "dataset"
    assert "Columns: city, population" in units[0].text()
    assert any("Tokyo | 13960000" in u.text() for u in units[1:])


def test_jsonl(tmp_path):
    f = tmp_path / "events.jsonl"
    f.write_text('{"event": "start", "n": 1}\n{"event": "stop", "n": 2}\n',
                 encoding="utf-8")
    rtype, units = ingest_file(f)
    assert rtype == "dataset"
    assert "2 records" in units[0].text()
    assert any('"event": "stop"' in u.text() for u in units)


def test_json_nested(tmp_path):
    f = tmp_path / "config.json"
    f.write_text(json.dumps({"server": {"port": 8373}, "flags": ["a", "b"]}),
                 encoding="utf-8")
    rtype, units = ingest_file(f)
    assert "Top-level shape: object{server, flags}" in units[0].text()
    assert any('"port": 8373' in u.text() for u in units)


def test_ipynb(tmp_path):
    nb = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Analysis\n", "Intro text."]},
            {"cell_type": "code", "source": ["x = 40 + 2\n", "print(x)"],
             "outputs": [{"text": ["42\n"]}]},
        ],
        "metadata": {"kernelspec": {"language": "python"}},
    }
    f = tmp_path / "nb.ipynb"
    f.write_text(json.dumps(nb), encoding="utf-8")
    rtype, units = ingest_file(f)
    assert rtype == "notebook"
    unit = units[0]
    assert unit.title == "Analysis"
    kinds = [c["kind"] for c in unit.content]
    assert "pre" in kinds
    assert "x = 40 + 2" in unit.text()
    assert "42" in unit.text()  # cell output captured


def test_sqlite(tmp_path):
    db = tmp_path / "app.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.executemany("INSERT INTO users (name) VALUES (?)",
                     [("ada",), ("grace",)])
    conn.commit()
    conn.close()
    rtype, units = ingest_file(db)
    assert rtype == "database"
    assert "Tables: users" in units[0].text()
    table_unit = next(u for u in units if u.title == "Table: users")
    assert "2 rows." in table_unit.text()
    assert "grace" in table_unit.text()
    assert "CREATE TABLE users" in table_unit.text()


def test_eml(tmp_path):
    f = tmp_path / "mail.eml"
    f.write_text(
        "From: ada@example.com\nTo: grace@example.com\n"
        "Subject: Spin report\nContent-Type: text/plain\n\n"
        "The widgets spun at 9000 rpm today.\n",
        encoding="utf-8",
    )
    rtype, units = ingest_file(f)
    assert rtype == "email"
    assert units[0].title == "Spin report"
    assert "9000 rpm" in units[0].text()


# ---------------------------------------------------------------- archives -

def test_zip_archive(tmp_path):
    src = tmp_path / "docs.zip"
    with zipfile.ZipFile(src, "w") as zf:
        zf.writestr("guide/intro.md", "# Intro\n\nWelcome to the archive.\n")
        zf.writestr("guide/data.csv", "k,v\na,1\n")
        zf.writestr("../evil.md", "# Evil\n\ntraversal\n")  # must be skipped
    rtype, units = ingest_file(src)
    joined = " ".join(u.text() for u in units)
    assert "Welcome to the archive" in joined
    assert "traversal" not in joined


# ------------------------------------------------------------------- repo --

def test_repo_dir(tmp_path):
    repo = tmp_path / "proj"
    (repo / ".git").mkdir(parents=True)          # marks it as a repo
    (repo / "src").mkdir()
    (repo / "README.md").write_text("# Proj\n\nSpins widgets.\n", encoding="utf-8")
    (repo / "src" / "main.py").write_text("def spin():\n    return 9000\n",
                                          encoding="utf-8")
    (repo / "src" / "util.js").write_text("export const rpm = 9000;\n",
                                          encoding="utf-8")
    result = build_pack_from_source(str(repo), tmp_path / "pack")
    reader = PackReader(tmp_path / "pack")
    assert reader.site["resource_type"] == "code"
    ids = reader.page_ids()
    assert "repo__000__tree" in ids
    hits = search_pack(reader, "spin widgets readme", top=3)
    assert hits
    py_unit = next(pid for pid in ids if "main-py" in pid)
    manifest = reader.page(py_unit)
    pre = [c for c in manifest["content"] if c["kind"] == "pre"]
    assert pre and pre[0].get("lang") == "py"


# ------------------------------------------------------------ cli software -

@pytest.fixture()
def fake_tool(tmp_path, monkeypatch):
    """A stub executable on PATH that answers --help/--version/sub --help."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "widgetctl"
    tool.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  --version) echo "widgetctl 3.1.4";;\n'
        '  --help) printf "usage: widgetctl <command>\\n\\ncommands:\\n'
        '  deploy    Deploy widgets to a region\\n'
        '  flush     Flush the widget cache\\n";;\n'
        '  deploy) echo "usage: widgetctl deploy --region REGION"; '
        'echo "Deploys widgets. Default region eu-west-1.";;\n'
        '  flush) echo "usage: widgetctl flush"; echo "Clears E42 stale cache.";;\n'
        "  *) exit 2;;\n"
        "esac\n"
    )
    tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return "widgetctl"


def test_cli_tool_ingestion(fake_tool, tmp_path):
    result = build_pack_from_cli_tool(fake_tool, tmp_path / "pack")
    reader = PackReader(tmp_path / "pack")
    assert reader.site["resource_type"] == "software"
    joined = " ".join(reader.page_markdown(pid) for pid in reader.page_ids())
    assert "widgetctl 3.1.4" in joined                 # version captured
    assert "Deploy widgets to a region" in joined      # main help
    assert "Default region eu-west-1" in joined        # subcommand help ran
    assert "E42 stale cache" in joined
    hits = search_pack(reader, "flush stale cache E42", top=2)
    assert hits


def test_cli_tool_not_installed(tmp_path):
    from agentic_anything.ingest_code import CodeError

    with pytest.raises(CodeError, match="not installed"):
        build_pack_from_cli_tool("definitely-not-a-real-tool-xyz", tmp_path / "p")


def test_cli_tool_name_validation(tmp_path):
    from agentic_anything.ingest_code import CodeError

    with pytest.raises(CodeError, match="invalid tool name"):
        build_pack_from_cli_tool("bad;rm -rf /", tmp_path / "p")


# ------------------------------------------------------------------ media --

@pytest.fixture()
def fake_media_tools(tmp_path, monkeypatch):
    """Stub ffmpeg/ffprobe/whisper that produce canned outputs."""
    bin_dir = tmp_path / "mediabin"
    bin_dir.mkdir()

    ffmpeg = bin_dir / "ffmpeg"
    ffmpeg.write_text(
        "#!/bin/sh\n"
        "# find the output path (last arg) and write an srt to it\n"
        'for last; do :; done\n'
        'printf "1\\n00:00:01,000 --> 00:00:03,000\\nEmbedded subtitle line.\\n" > "$last"\n'
    )
    ffprobe = bin_dir / "ffprobe"
    ffprobe.write_text(
        "#!/bin/sh\n"
        "echo '{\"format\": {\"duration\": \"93.5\"}, \"streams\": "
        "[{\"codec_type\": \"video\", \"codec_name\": \"h264\", \"width\": 1280, \"height\": 720}]}'\n"
    )
    for tool in (ffmpeg, ffprobe):
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return bin_dir


def test_local_video_embedded_subs(fake_media_tools, tmp_path):
    video = tmp_path / "talk.mp4"
    video.write_bytes(b"\x00fakevideo")
    rtype, units = ingest_file(video)
    assert rtype == "video"
    joined = " ".join(u.text() for u in units)
    assert "Embedded subtitle line." in joined
    assert "1m33s" in joined         # ffprobe metadata unit
    assert "h264 1280x720" in joined


def test_local_video_sidecar_wins(fake_media_tools, tmp_path):
    video = tmp_path / "talk.mp4"
    video.write_bytes(b"\x00fakevideo")
    (tmp_path / "talk.srt").write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nSidecar wins.\n", encoding="utf-8")
    _, units = ingest_file(video)
    joined = " ".join(u.text() for u in units)
    assert "Sidecar wins." in joined
    assert "Embedded subtitle line." not in joined


def test_local_media_no_tools(tmp_path, monkeypatch):
    from agentic_anything.ingest_media import MediaError

    monkeypatch.setenv("PATH", str(tmp_path / "emptybin"))
    audio = tmp_path / "note.mp3"
    audio.write_bytes(b"\x00fakeaudio")
    with pytest.raises((MediaError, IngestError), match="no transcript"):
        ingest_file(audio)


@pytest.fixture()
def fake_ytdlp(tmp_path, monkeypatch):
    bin_dir = tmp_path / "ytbin"
    bin_dir.mkdir()
    ytdlp = bin_dir / "yt-dlp"
    ytdlp.write_text(
        "#!/bin/sh\n"
        'if echo "$@" | grep -q dump-json; then\n'
        "  echo '{\"title\": \"Widget Physics 101\", \"uploader\": \"Prof X\", "
        "\"duration\": 300, \"description\": \"Three laws of widgets.\"}'\n"
        "else\n"
        "  # subtitle download: find -o template and write next to it\n"
        '  out=""\n'
        '  prev=""\n'
        '  for a; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done\n'
        '  printf "1\\n00:00:05,000 --> 00:00:09,000\\nThe first law of widgets.\\n" '
        '> "${out}.en.srt"\n'
        "fi\n"
    )
    ytdlp.chmod(ytdlp.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return "yt-dlp"


def test_remote_video(fake_ytdlp, tmp_path):
    from agentic_anything.ingest import build_pack_from_url_asset

    result = build_pack_from_url_asset(
        "https://www.youtube.com/watch?v=dummy123", tmp_path / "pack")
    reader = PackReader(tmp_path / "pack")
    assert reader.site["resource_type"] == "video"
    joined = " ".join(reader.page_markdown(pid) for pid in reader.page_ids())
    assert "Widget Physics 101" in joined
    assert "Prof X" in joined
    assert "The first law of widgets." in joined      # transcript ingested
    assert result.page_count >= 2


# ------------------------------------------------------ URL classification -

def test_classify_url():
    assert classify_url("https://www.youtube.com/watch?v=x") == "video"
    assert classify_url("https://youtu.be/x") == "video"
    assert classify_url("https://www.bilibili.com/video/BV1x") == "video"
    assert classify_url("https://example.com/movie.mp4") == "video"
    assert classify_url("https://github.com/psf/requests") == "repo"
    assert classify_url("https://github.com/psf/requests/tree/main") == "repo"
    assert classify_url("https://arxiv.org/abs/1706.03762") == "arxiv"
    assert classify_url("arxiv:1706.03762") == "arxiv"
    assert classify_url("https://x.com/paper.pdf") == "file"
    assert classify_url("https://x.com/data.csv?dl=1") == "file"
    assert classify_url("https://x.com/blog/feed.xml") == "feed"
    assert classify_url("https://x.com/rss") == "feed"
    assert classify_url("https://x.com/docs/guide") == "crawl"
    # github non-repo pages still crawl
    assert classify_url("https://github.com/psf/requests/issues/123") == "crawl"


# ----------------------------------------------------------------- feeds ---

def test_feed_parsing():
    from agentic_anything.ingest_data import parse_feed

    rss = b"""<?xml version="1.0"?><rss version="2.0"><channel>
      <title>Widget Weekly</title>
      <item><title>Issue 1</title><link>https://x.com/1</link>
        <pubDate>Mon, 01 Jul 2026</pubDate>
        <description>&lt;p&gt;Widgets spin up.&lt;/p&gt;</description>
        <enclosure url="https://x.com/ep1.mp3" type="audio/mpeg"/></item>
    </channel></rss>"""
    title, units = parse_feed(rss, "https://x.com/feed")
    assert title == "Widget Weekly"
    assert units[0].title == "Issue 1"
    text = units[0].text()
    assert "Widgets spin up." in text
    assert "audio enclosure: https://x.com/ep1.mp3" in text


def test_atom_parsing():
    from agentic_anything.ingest_data import parse_feed

    atom = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Atom Blog</title>
      <entry><title>Post A</title>
        <link href="https://x.com/a"/>
        <updated>2026-07-01</updated>
        <summary>Plain summary text.</summary></entry>
    </feed>"""
    title, units = parse_feed(atom, "https://x.com/atom.xml")
    assert title == "Atom Blog"
    assert "Plain summary text." in units[0].text()


# -------------------------------------------------- full-stack spot check --

def test_office_pack_full_stack(tmp_path):
    docx = _make_docx(tmp_path)
    build_pack_from_source(str(docx), tmp_path / "pack", site_id="report")
    reader = PackReader(tmp_path / "pack")
    hits = search_pack(reader, "revenue percent", top=2)
    assert hits
    from agentic_anything.skills import generate_skill

    skill = generate_skill(tmp_path / "pack", llm_config=None, use_llm=False)
    assert "report" in skill.read_text(encoding="utf-8")
