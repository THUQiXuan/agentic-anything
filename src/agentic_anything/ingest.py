"""Ingest non-web resources into the same agent-native pack format.

``build`` accepts more than URLs. Every adapter below converts a resource
into *units* (the generalization of pages): a book chapter, a markdown
section, a subtitle time-window, or a file in a folder each become one
unit with the same manifest schema web pages use — so ``chat``, ``skill``,
``clify``, ``query`` and ``serve`` work identically on all of them.

Supported sources (v0.2):

- ``.txt``            plain text, split on blank-line groups / size budget
- ``.md`` / ``.markdown``  split by headings
- ``.epub``            zipfile + the built-in HTML parser (zero extra deps)
- ``.pdf``             requires the ``[docs]`` extra (pypdf)
- ``.srt`` / ``.vtt``  video/audio transcripts, split into time windows
- a directory          every supported file inside becomes a unit group
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from ._version import __version__
from .markdown import page_to_markdown
from .parser import parse_html
from .util import sha256_bytes, slugify, truncate_text, utc_now_iso, write_json

SPEC_VERSION = "0.2"

DOCUMENT_EXTENSIONS = {".txt", ".md", ".markdown", ".epub", ".pdf", ".srt", ".vtt", ".html", ".htm"}

# Units bigger than this are split (characters of content text).
_MAX_UNIT_CHARS = 12_000
_MIN_UNIT_CHARS = 200


@dataclass
class Unit:
    unit_id: str
    title: str
    kind: str                    # chapter | section | segment | file | page
    content: list[dict] = field(default_factory=list)  # same stream schema as web pages
    source_path: str = ""
    locator: str = ""            # e.g. "chapter 3", "00:12:40–00:15:00", "pages 10-14"
    meta: dict = field(default_factory=dict)

    def text(self) -> str:
        return "\n".join(c.get("text", "") for c in self.content)


class IngestError(ValueError):
    pass


def detect_source_kind(source: str) -> str:
    """'web' | 'file' | 'dir' for a build source string."""
    if re.match(r"^https?://", source):
        return "web"
    path = Path(source).expanduser()
    if path.is_dir():
        return "dir"
    if path.is_file():
        return "file"
    # not an existing path and no scheme: a bare host like
    # 'example.com', 'example.com/docs' or '127.0.0.1:8080/x' is web —
    # but a missing local file with a known document extension is a typo.
    head = source.split("/", 1)[0]
    if head.lower().endswith(tuple(DOCUMENT_EXTENSIONS)):
        raise IngestError(f"file not found: {source}")
    if "." in head or head.split(":")[0] == "localhost":
        return "web"
    raise IngestError(
        f"cannot ingest '{source}': not a URL, existing file, or directory"
    )


# --------------------------------------------------------------------------
# adapters: file -> list[Unit]
# --------------------------------------------------------------------------

def ingest_file(path: Path) -> tuple[str, list[Unit]]:
    """Returns (resource_type, units)."""
    suffix = path.suffix.lower()
    if suffix in (".txt",):
        return "document", _ingest_text(path)
    if suffix in (".md", ".markdown"):
        return "document", _ingest_markdown(path)
    if suffix == ".epub":
        return "book", _ingest_epub(path)
    if suffix == ".pdf":
        return "document", _ingest_pdf(path)
    if suffix in (".srt", ".vtt"):
        return "video", _ingest_subtitles(path)
    if suffix in (".html", ".htm"):
        return "document", _ingest_html_file(path)
    raise IngestError(
        f"unsupported file type '{suffix}' "
        f"(supported: {', '.join(sorted(DOCUMENT_EXTENSIONS))})"
    )


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    # BOMs first: they are unambiguous.
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    # gb18030 decodes almost any byte stream "successfully" — and cp1252
    # mojibake yields scattered CJK too — so require a substantial CJK
    # DENSITY before trusting it; otherwise assume cp1252.
    try:
        text = data.decode("gb18030")
        sample = [ch for ch in text[:4000] if not ch.isspace()]
        cjk = sum(1 for ch in sample if "一" <= ch <= "鿿")
        if sample and cjk / len(sample) >= 0.3:
            return text
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def _unit_id(base: str, index: int, title: str) -> str:
    slug = slugify(title, 40)
    return f"{base}__{index:03d}" + (f"__{slug}" if slug and slug != "site" else "")


def _ingest_text(path: Path) -> list[Unit]:
    text = _read_text(path)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[Unit] = []
    buf: list[str] = []
    size = 0
    base = slugify(path.stem, 40)

    def flush() -> None:
        nonlocal buf, size
        if not buf:
            return
        index = len(units) + 1
        first_line = buf[0].splitlines()[0]
        title = truncate_text(first_line, 80) or f"part {index}"
        units.append(
            Unit(
                unit_id=_unit_id(base, index, title),
                title=title,
                kind="section",
                content=[{"kind": "p", "text": p} for p in buf],
                source_path=str(path),
                locator=f"part {index}",
            )
        )
        buf, size = [], 0

    for para in paragraphs:
        buf.append(para)
        size += len(para)
        if size >= _MAX_UNIT_CHARS:
            flush()
    flush()
    return units


_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")


def _ingest_markdown(path: Path) -> list[Unit]:
    """Split by ATX headings with CommonMark-style fence awareness.

    A fence opened with N backticks/tildes only closes on >= N of the SAME
    character; heading detection and paragraph splitting both respect fences.
    """
    lines = _read_text(path).splitlines()
    base = slugify(path.stem, 40)

    # Each section: (title, level, items) where items are content dicts.
    sections: list[tuple[str, int, list[dict]]] = []
    title, level = path.stem, 0
    items: list[dict] = []
    para: list[str] = []
    fence_char = ""      # "`" or "~" while inside a fence
    fence_len = 0
    code: list[str] = []
    code_lang = ""

    def flush_para() -> None:
        nonlocal para
        text = "\n".join(para).strip()
        para = []
        if text:
            items.append({"kind": "p", "text": text})

    def flush_code() -> None:
        nonlocal code, code_lang
        text = "\n".join(code)
        code, lang = [], code_lang
        code_lang = ""
        entry: dict = {"kind": "pre", "text": text}
        if lang:
            entry["lang"] = lang
        items.append(entry)

    def flush_section() -> None:
        nonlocal items, title, level
        sections.append((title, level, items))
        items = []

    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_char:
            if (fence_match and fence_match.group(2)[0] == fence_char
                    and len(fence_match.group(2)) >= fence_len
                    and not fence_match.group(3).strip()):
                fence_char = ""
                flush_code()
            else:
                code.append(line)
            continue
        if fence_match:
            flush_para()
            fence_char = fence_match.group(2)[0]
            fence_len = len(fence_match.group(2))
            code_lang = fence_match.group(3).strip()
            continue
        heading = _MD_HEADING_RE.match(line)
        if heading and heading.group(2):
            flush_para()
            flush_section()
            title, level = heading.group(2), len(heading.group(1))
            items.append({"kind": "heading", "level": level, "text": title})
            continue
        if not line.strip():
            flush_para()
        else:
            para.append(line)

    if fence_char:  # unterminated fence at EOF
        flush_code()
    flush_para()
    flush_section()

    units: list[Unit] = []
    for section_title, section_level, section_items in sections:
        if not section_items and len(sections) > 1:
            continue
        index = len(units) + 1
        units.append(
            Unit(
                unit_id=_unit_id(base, index, section_title),
                title=section_title,
                kind="section",
                content=section_items,
                source_path=str(path),
                locator=f"section {index}",
            )
        )
    # Sections are author-chosen retrieval units — never merge them.
    return units


def _ingest_html_file(path: Path) -> list[Unit]:
    structure = parse_html(_read_text(path), f"file://{path}")
    title = structure.title or path.stem
    return [
        Unit(
            unit_id=slugify(path.stem, 60) or "document",
            title=title,
            kind="page",
            content=list(structure.content),
            source_path=str(path),
            locator=path.name,
        )
    ]


def _ingest_epub(path: Path) -> list[Unit]:
    """EPUB = zip of XHTML chapters; spine order from the OPF manifest."""
    units: list[Unit] = []
    base = slugify(path.stem, 40)
    try:
        book = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise IngestError(f"not a valid EPUB (bad zip): {path}") from exc
    with book:
        names = book.namelist()
        # The authoritative OPF location is META-INF/container.xml; fall back
        # to the first *.opf only when it is absent or unparseable.
        opf_name = None
        if "META-INF/container.xml" in names:
            container = book.read("META-INF/container.xml").decode("utf-8", errors="replace")
            match = re.search(r"""<rootfile[^>]+full-path=["']([^"']+)["']""", container)
            if match and match.group(1) in names:
                opf_name = match.group(1)
        if opf_name is None:
            opf_name = next((n for n in names if n.lower().endswith(".opf")), None)
        ordered: list[str] = []
        if opf_name:
            opf = book.read(opf_name).decode("utf-8", errors="replace")
            # word-boundary before attribute names so media-overlay-id etc.
            # cannot be mistaken for id=
            manifest = dict(re.findall(
                r"""<item\b[^>]*?[\s"']id=["']([^"']+)["'][^>]*?[\s"']href=["']([^"']+)["']""",
                opf,
            ) + [
                (m, h) for h, m in re.findall(
                    r"""<item\b[^>]*?[\s"']href=["']([^"']+)["'][^>]*?[\s"']id=["']([^"']+)["']""",
                    opf,
                )
            ])
            opf_dir = str(Path(opf_name).parent)
            for idref in re.findall(r"""<itemref\b[^>]*?[\s"']idref=["']([^"']+)["']""", opf):
                href = manifest.get(idref)
                if href:
                    full = href if opf_dir in ("", ".") else f"{opf_dir}/{href}"
                    if full in names:
                        ordered.append(full)
        if not ordered:
            ordered = sorted(
                n for n in names if n.lower().endswith((".xhtml", ".html", ".htm"))
            )
        for index, name in enumerate(ordered, 1):
            html = book.read(name).decode("utf-8", errors="replace")
            structure = parse_html(html, f"epub://{path.name}/{name}")
            content = list(structure.content)
            if not content:
                continue
            title = structure.title or (
                structure.headings[0].text if structure.headings else Path(name).stem
            )
            units.append(
                Unit(
                    unit_id=_unit_id(base, index, title),
                    title=title,
                    kind="chapter",
                    content=content,
                    source_path=f"{path}!{name}",
                    locator=f"chapter {index}",
                )
            )
    if not units:
        raise IngestError(f"no readable chapters found in EPUB: {path}")
    return _split_large_units(_merge_small_units(units))


def _ingest_pdf(path: Path) -> list[Unit]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise IngestError(
            "PDF ingestion requires the [docs] extra:\n"
            "  pip install 'agentic-anything[docs]'"
        ) from exc
    reader = PdfReader(str(path))
    base = slugify(path.stem, 40)
    units: list[Unit] = []
    buf: list[str] = []
    start_page = 1
    size = 0
    for page_no, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text.strip()
        if text:
            buf.append(text)
            size += len(text)
        if size >= _MAX_UNIT_CHARS or page_no == len(reader.pages):
            if buf:
                index = len(units) + 1
                locator = (
                    f"pages {start_page}-{page_no}" if page_no > start_page
                    else f"page {page_no}"
                )
                units.append(
                    Unit(
                        unit_id=_unit_id(base, index, locator),
                        title=f"{path.stem} — {locator}",
                        kind="segment",
                        content=[{"kind": "p", "text": t} for t in buf],
                        source_path=str(path),
                        locator=locator,
                    )
                )
            buf, size, start_page = [], 0, page_no + 1
    if not units:
        raise IngestError(
            f"no extractable text in PDF: {path} (scanned images need OCR first)"
        )
    return units


_SRT_TIME = re.compile(
    r"(?:(\d{1,3}):)?(\d{1,2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d{1,3}):)?(\d{1,2}):(\d{2})[.,](\d{3})"
)
_VTT_TAG = re.compile(r"<[^>]+>")
_WINDOW_SECONDS = 180  # one unit per ~3 minutes of transcript


def _ingest_subtitles(path: Path) -> list[Unit]:
    text = _read_text(path)
    base = slugify(path.stem, 40)
    cues: list[tuple[float, float, str]] = []
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        match = _SRT_TIME.search(block)
        if not match:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(g or 0) for g in match.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        # Drop the remainder of the timing line (VTT cue settings like
        # 'position:10% align:start'); cue text starts on the next line.
        after = block[match.end():]
        after = after.split("\n", 1)[1] if "\n" in after else ""
        cue_lines = [
            _VTT_TAG.sub("", ln).strip() for ln in after.splitlines() if ln.strip()
        ]
        cue_text = " ".join(ln for ln in cue_lines if ln)
        if cue_text:
            cues.append((start, end, cue_text))
    if not cues:
        raise IngestError(f"no subtitle cues found in {path}")
    cues.sort(key=lambda c: (c[0], c[1]))

    def fmt(seconds: float) -> str:
        seconds = int(seconds)
        return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"

    units: list[Unit] = []
    window: list[tuple[float, float, str]] = []
    window_start = cues[0][0]
    for cue in cues:
        if window and cue[0] - window_start >= _WINDOW_SECONDS:
            units.append(_subtitle_unit(base, len(units) + 1, window, fmt))
            window = []
            window_start = cue[0]
        window.append(cue)
    if window:
        units.append(_subtitle_unit(base, len(units) + 1, window, fmt))
    for unit in units:
        unit.source_path = str(path)
    return units


def _subtitle_unit(base: str, index: int, cues, fmt) -> Unit:
    start = cues[0][0]
    end = max(c[1] for c in cues)  # a long cue can outlast later short cues
    locator = f"{fmt(start)}–{fmt(end)}"
    text = " ".join(c[2] for c in cues)
    return Unit(
        unit_id=f"{base}__{index:03d}__{fmt(start).replace(':', '-')}",
        title=f"transcript {locator}",
        kind="segment",
        content=[{"kind": "p", "text": text}],
        locator=locator,
        meta={"start_seconds": round(start, 3), "end_seconds": round(end, 3)},
    )


def _merge_small_units(units: list[Unit]) -> list[Unit]:
    """Merge consecutive tiny units (cover pages, single-line sections)."""
    merged: list[Unit] = []
    for unit in units:
        if merged and len(unit.text()) < _MIN_UNIT_CHARS and merged[-1].kind == unit.kind:
            prev = merged[-1]
            prev.content.extend(unit.content)
            continue
        merged.append(unit)
    return merged


def _split_large_units(units: list[Unit]) -> list[Unit]:
    out: list[Unit] = []
    for unit in units:
        if len(unit.text()) <= _MAX_UNIT_CHARS * 2:
            out.append(unit)
            continue
        parts: list[list[dict]] = []
        part: list[dict] = []
        size = 0
        for item in unit.content:
            part.append(item)
            size += len(item.get("text", ""))
            if size >= _MAX_UNIT_CHARS:
                parts.append(part)
                part, size = [], 0
        if part:
            parts.append(part)
        if len(parts) <= 1:  # nothing actually split — keep the unit as-is
            out.append(unit)
            continue
        for part_no, part_items in enumerate(parts, 1):
            out.append(Unit(
                unit_id=f"{unit.unit_id}__p{part_no}",
                title=f"{unit.title} (part {part_no})",
                kind=unit.kind,
                content=part_items,
                source_path=unit.source_path,
                locator=f"{unit.locator} part {part_no}",
                meta=dict(unit.meta),
            ))
    return out


def ingest_directory(path: Path) -> tuple[str, list[Unit], list[str]]:
    units: list[Unit] = []
    warnings: list[str] = []
    files = sorted(
        p for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in DOCUMENT_EXTENSIONS
        # skip hidden files/dirs INSIDE the corpus only (not absolute ancestors)
        and not any(part.startswith(".") for part in p.relative_to(path).parts)
    )
    if not files:
        raise IngestError(
            f"no supported files under {path} "
            f"(looking for {', '.join(sorted(DOCUMENT_EXTENSIONS))})"
        )
    for file_path in files:
        rel = file_path.relative_to(path)
        try:
            _, file_units = ingest_file(file_path)
        except IngestError as exc:
            warnings.append(f"skipped {rel}: {exc}")
            continue
        # Prefix from the FULL relative path including the suffix, so
        # a/b.md vs a-b.md vs a/b.txt never collide.
        prefix_parts = [slugify(part, 40) or "x" for part in rel.parts[:-1]]
        prefix_parts.append(slugify(rel.name, 50) or "x")  # keeps the extension
        prefix = "--".join(prefix_parts)[:80]
        for unit in file_units:
            unit.unit_id = f"{prefix}__{unit.unit_id}"[:150]
            unit.locator = f"{rel} · {unit.locator}" if unit.locator else str(rel)
        units.extend(file_units)
    return "collection", units, warnings


# --------------------------------------------------------------------------
# pack writer (shared shape with the web packer)
# --------------------------------------------------------------------------

def build_pack_from_source(source: str, output_dir: str | Path, site_id: str | None = None):
    """Ingest a local file/directory into a pack. Returns a BuildResult."""
    from .packer import BuildResult

    path = Path(source).expanduser().resolve()
    warnings: list[str] = []
    if path.is_dir():
        resource_type, units, warnings = ingest_directory(path)
        default_id = slugify(path.name, 60)
    else:
        resource_type, units = ingest_file(path)
        default_id = slugify(path.stem, 60)
    site_id = site_id or default_id or "resource"

    pack_dir = Path(output_dir).resolve()
    pack_dir.mkdir(parents=True, exist_ok=True)
    started = utc_now_iso()

    # de-duplicate unit ids defensively
    seen: set[str] = set()
    for unit in units:
        if unit.unit_id in seen:
            n = 2
            while f"{unit.unit_id}~{n}" in seen:
                n += 1
            unit.unit_id = f"{unit.unit_id}~{n}"
        seen.add(unit.unit_id)

    index_entries = []
    for unit in units:
        manifest = {
            "spec_version": SPEC_VERSION,
            "page_id": unit.unit_id,
            "source_url": unit.source_path,
            "url_path": unit.locator,
            "title": unit.title,
            "page_type": unit.kind,
            "unit_kind": unit.kind,
            "locator": unit.locator,
            "summary": truncate_text(unit.text(), 240),
            "content": unit.content,
            "links": [],
            "outgoing_page_ids": [],
            "forms": [],
            "images": [],
            "provenance": {
                "source_path": unit.source_path,
                "capture_mode": "ingest",
                "content_sha256": sha256_bytes(unit.text().encode("utf-8", "replace")),
                **({k: v for k, v in unit.meta.items()} if unit.meta else {}),
            },
        }
        write_json(pack_dir / "pages" / f"{unit.unit_id}.json", manifest)
        (pack_dir / "pages" / f"{unit.unit_id}.md").write_text(
            page_to_markdown(manifest), encoding="utf-8"
        )
        index_entries.append({
            "page_id": unit.unit_id,
            "url": unit.source_path,
            "url_path": unit.locator,
            "title": unit.title,
            "page_type": unit.kind,
            "summary": manifest["summary"],
            "outgoing_page_ids": [],
            "form_count": 0,
            "discovered_via": "ingest",
            "depth": 0,
            "rendered": False,
            "has_screenshot": False,
        })

    snapshot = {
        "spec_version": SPEC_VERSION,
        "generator": f"agentic-anything/{__version__}",
        "site_id": site_id,
        "resource_type": resource_type,
        "seed_url": str(path),
        "captured_at": started,
        "finished_at": utc_now_iso(),
        "capture_mode": "ingest",
        "respect_robots": None,
        "same_origin_only": None,
        "max_pages": None,
        "page_count": len(units),
        "pages": index_entries,
        "frontier": [],
        "notes": warnings,
    }
    write_json(pack_dir / "site.json", snapshot)
    write_json(pack_dir / "api" / "apis.json", {
        "endpoints": [], "forms": [], "openapi": [], "well_known": [],
        "feeds": [], "sitemaps": [], "observed_network": [],
    })
    write_json(pack_dir / "agent-pack.json", {
        "spec_version": SPEC_VERSION,
        "kind": "agentic-anything-pack",
        "site_id": site_id,
        "site_name": units[0].title if len(units) == 1 else path.name,
        "resource_type": resource_type,
        "seed_url": str(path),
        "generated_at": started,
        "generator": f"agentic-anything/{__version__}",
        "capabilities": ["site_snapshot", "page_index", "page_manifests",
                         "markdown_views", "api_surface"],
        "contents": {
            "site_snapshot": "site.json",
            "page_manifests": "pages/*.json",
            "markdown_views": "pages/*.md",
            "api_surface": "api/apis.json",
            "skill": "skills/SKILL.md",
        },
    })

    return BuildResult(
        pack_dir=pack_dir,
        site_id=site_id,
        page_count=len(units),
        frontier_count=0,
        api_count=0,
        warnings=warnings + ([] if units else ["no units ingested"]),
    )
