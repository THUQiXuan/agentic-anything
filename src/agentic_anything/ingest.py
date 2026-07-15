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

# Text-family formats handled by the built-in splitters.
TEXT_EXTENSIONS = {".txt", ".rst", ".log", ".yaml", ".yml", ".toml", ".ini",
                   ".cfg", ".tex", ".text"}
MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx"}
DATA_EXTENSIONS = {".csv", ".tsv", ".json", ".jsonl", ".ipynb",
                   ".db", ".sqlite", ".sqlite3", ".eml", ".mbox"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".tgz"}  # plus .tar.gz via name check
SUBTITLE_EXTENSIONS = {".srt", ".vtt"}

# Everything ingestible as a single file (directory walking uses a subset).
DOCUMENT_EXTENSIONS = (
    TEXT_EXTENSIONS | MARKDOWN_EXTENSIONS | OFFICE_EXTENSIONS | DATA_EXTENSIONS
    | SUBTITLE_EXTENSIONS | {".epub", ".pdf", ".html", ".htm"}
)
# Directory walking excludes archives (recursion risk) and media (tool-heavy),
# but media files inside a folder are still attempted, with warnings on skip.
_DIR_WALK_EXTENSIONS = DOCUMENT_EXTENSIONS

# Units bigger than this are split (characters of content text).
_MAX_UNIT_CHARS = 12_000
_MIN_UNIT_CHARS = 200
_MAX_PDF_PAGES_PER_UNIT = 8   # keep PDF citations page-addressable
_MAX_ARCHIVE_MEMBERS = 4000
_MAX_ARCHIVE_BYTES = 500_000_000  # decompressed cap (zip-bomb guard)


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
    from .ingest_media import MEDIA_EXTENSIONS

    suffix = path.suffix.lower()
    name_lower = path.name.lower()
    if suffix in TEXT_EXTENSIONS:
        return "document", _ingest_text(path)
    if suffix in MARKDOWN_EXTENSIONS:
        return "document", _ingest_markdown(path)
    if suffix == ".epub":
        return "book", _ingest_epub(path)
    if suffix == ".pdf":
        return "document", _ingest_pdf(path)
    if suffix in SUBTITLE_EXTENSIONS:
        return "video", _ingest_subtitles(path)
    if suffix in (".html", ".htm"):
        return "document", _ingest_html_file(path)
    if suffix == ".docx":
        from .ingest_office import ingest_docx

        return "document", ingest_docx(path)
    if suffix == ".pptx":
        from .ingest_office import ingest_pptx

        return "presentation", ingest_pptx(path)
    if suffix == ".xlsx":
        from .ingest_office import ingest_xlsx

        return "dataset", ingest_xlsx(path)
    if suffix in (".csv", ".tsv"):
        from .ingest_data import ingest_csv

        return "dataset", ingest_csv(path)
    if suffix in (".json", ".jsonl"):
        from .ingest_data import ingest_json

        return "dataset", ingest_json(path)
    if suffix == ".ipynb":
        from .ingest_data import ingest_ipynb

        return "notebook", ingest_ipynb(path)
    if suffix in (".db", ".sqlite", ".sqlite3"):
        from .ingest_data import ingest_sqlite

        return "database", ingest_sqlite(path)
    if suffix == ".eml":
        from .ingest_data import ingest_eml

        return "email", ingest_eml(path)
    if suffix == ".mbox":
        from .ingest_data import ingest_mbox

        return "email", ingest_mbox(path)
    if suffix in MEDIA_EXTENSIONS:
        from .ingest_media import ingest_local_media

        resource = "audio" if suffix in {".mp3", ".wav", ".m4a", ".flac",
                                         ".ogg", ".opus", ".aac"} else "video"
        return resource, ingest_local_media(path)
    if suffix in ARCHIVE_EXTENSIONS or name_lower.endswith(".tar.gz"):
        return _ingest_archive(path)
    raise IngestError(
        f"unsupported file type '{suffix}' "
        f"(supported: {', '.join(sorted(DOCUMENT_EXTENSIONS | ARCHIVE_EXTENSIONS | MEDIA_EXTENSIONS))})"
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
        # split on the char budget, on the page-window cap (slide decks carry
        # little text per page — citations must still stay page-addressable),
        # or at the end of the document
        if (size >= _MAX_UNIT_CHARS
                or (page_no - start_page + 1) >= _MAX_PDF_PAGES_PER_UNIT
                or page_no == len(reader.pages)):
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

    def stamp(seconds: float) -> str:
        whole = int(seconds)
        millis = round((seconds - whole) * 1000)
        return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}.{millis:03d}"

    # One line per cue, prefixed with its exact time range: timecodes are the
    # evidence a video/audio agent needs (finding moments, cutting clips).
    lines = [f"[{stamp(c[0])} → {stamp(c[1])}] {c[2]}" for c in cues]
    return Unit(
        unit_id=f"{base}__{index:03d}__{fmt(start).replace(':', '-')}",
        title=f"transcript {locator}",
        kind="segment",
        content=[{"kind": "pre", "text": "\n".join(lines)}],
        locator=locator,
        meta={"start_seconds": round(start, 3), "end_seconds": round(end, 3),
              "cue_count": len(cues)},
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
    # A source tree is ingested as code (tree overview + per-file units).
    from .ingest_code import ingest_repo_dir, looks_like_repo

    if looks_like_repo(path):
        return "code", ingest_repo_dir(path), []
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
# archives
# --------------------------------------------------------------------------

def _safe_extract_zip(zip_path: Path, dest: Path) -> None:
    """Extract a zip while refusing traversal, symlinks and decompression bombs."""
    dest.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(zip_path) as book:
        members = book.infolist()
        if len(members) > _MAX_ARCHIVE_MEMBERS:
            raise IngestError(f"archive has too many members ({len(members)})")
        for member in members:
            name = member.filename
            target = (dest / name).resolve()
            if not str(target).startswith(str(dest.resolve())):
                continue  # path traversal attempt
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            # skip symlinks (external attr high byte 0xA = symlink)
            if (member.external_attr >> 28) == 0xA:
                continue
            total += member.file_size
            if total > _MAX_ARCHIVE_BYTES:
                raise IngestError("archive decompresses beyond the 500MB cap")
            target.parent.mkdir(parents=True, exist_ok=True)
            with book.open(member) as src, open(target, "wb") as dst:
                remaining = _MAX_ARCHIVE_BYTES
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    if remaining < 0:
                        raise IngestError("archive decompresses beyond the 500MB cap")
                    dst.write(chunk)


def _safe_extract_tar(tar_path: Path, dest: Path) -> None:
    import tarfile

    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path) as book:
        members = book.getmembers()
        if len(members) > _MAX_ARCHIVE_MEMBERS:
            raise IngestError(f"archive has too many members ({len(members)})")
        total = 0
        safe = []
        for member in members:
            if not (member.isfile() or member.isdir()):
                continue  # no symlinks/devices
            target = (dest / member.name).resolve()
            if not str(target).startswith(str(dest.resolve())):
                continue
            total += member.size
            if total > _MAX_ARCHIVE_BYTES:
                raise IngestError("archive decompresses beyond the 500MB cap")
            safe.append(member)
        book.extractall(dest, members=safe)  # noqa: S202 - members pre-filtered


def _ingest_archive(path: Path) -> tuple[str, list[Unit]]:
    import tempfile

    workdir = Path(tempfile.mkdtemp(prefix="aany_archive_"))
    if path.suffix.lower() == ".zip":
        _safe_extract_zip(path, workdir)
    else:
        _safe_extract_tar(path, workdir)
    roots = [p for p in workdir.iterdir()]
    root = roots[0] if len(roots) == 1 and roots[0].is_dir() else workdir
    resource_type, units, warnings = ingest_directory(root)
    for unit in units:
        unit.source_path = f"{path}!{Path(unit.source_path).name}" \
            if unit.source_path else str(path)
        unit.meta.setdefault("archive", str(path))
    if warnings:
        units[0].meta["ingest_warnings"] = warnings
    return ("archive" if resource_type == "collection" else resource_type), units


# --------------------------------------------------------------------------
# URL assets (non-crawl sources reachable by URL)
# --------------------------------------------------------------------------

_ARXIV_RE = re.compile(
    r"^(?:arxiv:|https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/)"
    r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(v\d+)?(?:\.pdf)?/?$",
    re.IGNORECASE,
)
_GITHUB_BLOB_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/([\w.\-]+)/([\w.\-]+)/(?:blob|raw)/([\w.\-/%]+)$"
)
_FILE_URL_EXTENSIONS = DOCUMENT_EXTENSIONS - {".html", ".htm"}
_MAX_DOWNLOAD_BYTES = 80_000_000


def classify_url(url: str) -> str:
    """'crawl' | 'video' | 'repo' | 'arxiv' | 'file' | 'feed' for a URL."""
    from urllib.parse import urlsplit

    from .ingest_code import is_github_repo_url
    from .ingest_media import is_video_url

    bare = url.split("?")[0].split("#")[0]
    if _ARXIV_RE.match(bare):
        return "arxiv"
    if is_github_repo_url(url):
        return "repo"
    if _GITHUB_BLOB_RE.match(bare):
        return "file"  # rewritten to raw.githubusercontent.com when fetched
    if is_video_url(url):
        return "video"
    # Extension checks apply to the URL *path* only — a bare host whose TLD
    # collides with an extension (gov.md, example.zip) must still crawl.
    path = urlsplit(bare).path if "://" in bare else "/" + bare.split("/", 1)[-1]
    lower = path.lower()
    if lower in ("", "/"):
        return "crawl"
    if lower.endswith(tuple(_FILE_URL_EXTENSIONS)) or lower.endswith(".tar.gz") \
            or lower.endswith(tuple(ARCHIVE_EXTENSIONS)):
        return "file"
    if lower.endswith(("/feed", "/feed/", "/rss", "/rss/", "/feed.xml",
                       "/rss.xml", "/atom.xml", ".rss", ".atom")):
        return "feed"
    return "crawl"


def build_pack_from_url_asset(url: str, output_dir: str | Path,
                              site_id: str | None = None):
    """Ingest a non-crawl URL (video, repo, arXiv, direct file, feed)."""
    from .fetcher import fetch
    from .util import site_slug_from_url

    kind = classify_url(url)
    if kind == "crawl":
        raise IngestError(f"{url} is a regular website; use the crawler path")

    if kind == "video":
        from .ingest_media import ingest_remote_video

        title, units = ingest_remote_video(url)
        return _write_units_pack(
            units, "video", site_id or slugify(title, 60) or "video",
            output_dir, source_label=url)

    if kind == "repo":
        asset = units_for_url_asset(url)
        return _write_units_pack(
            asset.units, "code", site_id or slugify(asset.title, 60) or "repo",
            output_dir, source_label=url)

    if kind == "arxiv":
        match = _ARXIV_RE.match(url.split("?")[0].split("#")[0])
        paper_id = match.group(1) + (match.group(2) or "")
        asset = units_for_url_asset(url)
        return _write_units_pack(
            asset.units, "paper",
            site_id or "arxiv-" + slugify(paper_id.replace("/", "-"), 40),
            output_dir, source_label=asset.source_label)

    if kind == "feed":
        from .ingest_data import DataError, parse_feed

        result = fetch(url, timeout=30, max_bytes=_MAX_DOWNLOAD_BYTES, retries=1)
        if not result.ok:
            raise IngestError(f"could not fetch feed {url} (HTTP {result.status})")
        try:
            feed_title, units = parse_feed(result.body, url)
        except DataError as exc:
            raise IngestError(
                f"{url} does not look like an RSS/Atom feed ({exc}); "
                "try building it as a website instead"
            ) from exc
        return _write_units_pack(
            units, "feed", site_id or slugify(feed_title, 60) or "feed",
            output_dir, source_label=url)

    # kind == "file": download then reuse the local-file adapters
    from urllib.parse import unquote

    bare = url.split("?")[0].split("#")[0]
    asset = units_for_url_asset(url)
    filename = Path(unquote(bare)).name or "download"
    return _write_units_pack(
        asset.units, asset.resource_type,
        site_id or slugify(Path(filename).stem, 60) or site_slug_from_url(url),
        output_dir, source_label=url)


def _check_downloaded_body(filename: str, result) -> None:
    """A .pdf/.docx/... URL that returns an HTML page (login wall, soft-404)
    must fail loudly instead of ingesting markup as document content."""
    suffix = Path(filename).suffix.lower()
    if suffix in (".html", ".htm"):
        return
    body = result.body.lstrip()[:512]
    looks_html = result.is_html or body[:1] == b"<" and (
        b"<html" in body.lower() or b"<!doctype" in body.lower())
    if looks_html:
        raise IngestError(
            f"the server returned an HTML page instead of a {suffix} file "
            "(login wall, soft-404, or share-preview page?); "
            "use the direct download link, or build it as a website"
        )
    if suffix == ".pdf" and not result.body.startswith(b"%PDF"):
        raise IngestError("downloaded file is not a valid PDF")
    if suffix in (".zip", ".docx", ".pptx", ".xlsx", ".epub") \
            and result.body[:2] != b"PK":
        raise IngestError(f"downloaded file is not a valid {suffix} archive")


@dataclass
class AssetIngest:
    """Units extracted from a non-crawl URL, plus download provenance."""

    kind: str            # classify_url() kind: 'file' | 'repo' | 'arxiv'
    resource_type: str   # pack-level resource type ('code', 'paper', ...)
    title: str
    units: list[Unit]
    source_label: str    # canonical source URL for provenance
    fetched_url: str     # URL actually downloaded (raw/codeload rewrite)
    content_sha256: str
    content_bytes: int


def direct_fetch_url(url: str) -> str:
    """The URL actually requested when ingesting ``url`` as a non-crawl asset.

    GitHub blob pages rewrite to raw.githubusercontent.com, repositories to
    their codeload zip export, arXiv ids to the PDF endpoint. Used both for
    fetching and for policy checks (robots) against the real target.
    """
    bare = url.split("?")[0].split("#")[0]
    blob = _GITHUB_BLOB_RE.match(bare)
    if blob:
        return (f"https://raw.githubusercontent.com/"
                f"{blob.group(1)}/{blob.group(2)}/{blob.group(3)}")
    kind = classify_url(url)
    if kind == "repo":
        from .ingest_code import codeload_zip_urls

        return codeload_zip_urls(url)[0]
    if kind == "arxiv":
        match = _ARXIV_RE.match(bare)
        paper_id = match.group(1) + (match.group(2) or "")
        return f"https://arxiv.org/pdf/{paper_id}"
    return url


def units_for_url_asset(url: str, *, max_bytes: int | None = None,
                        timeout: float = 60.0) -> AssetIngest:
    """Fetch and ingest a 'file' / 'repo' / 'arxiv' URL into units.

    This is ``build_pack_from_url_asset`` without the pack writing — the
    building block for merging linked documents and repositories into a
    site pack (deep capture) as well as for standalone asset packs.
    """
    import tempfile

    from .fetcher import fetch

    cap = max_bytes or _MAX_DOWNLOAD_BYTES
    kind = classify_url(url)

    if kind == "repo":
        from .ingest_code import ingest_github_url

        meta: dict = {}
        repo_name, units = ingest_github_url(
            url, timeout=max(timeout, 60.0), max_bytes=cap, meta=meta)
        return AssetIngest(
            kind="repo", resource_type="code", title=repo_name, units=units,
            source_label=url, fetched_url=meta.get("fetched_url", url),
            content_sha256=meta.get("content_sha256", ""),
            content_bytes=meta.get("content_bytes", 0),
        )

    if kind == "arxiv":
        match = _ARXIV_RE.match(url.split("?")[0].split("#")[0])
        paper_id = match.group(1) + (match.group(2) or "")
        pdf_url = f"https://arxiv.org/pdf/{paper_id}"
        result = fetch(pdf_url, timeout=max(timeout, 60.0), max_bytes=cap, retries=1)
        if not result.ok or not result.body.startswith(b"%PDF"):
            raise IngestError(f"could not download arXiv paper {paper_id}")
        if len(result.body) >= cap:
            raise IngestError(f"arXiv paper {paper_id} exceeds the {cap // 1_000_000}MB cap")
        workdir = Path(tempfile.mkdtemp(prefix="aany_arxiv_"))
        pdf_path = workdir / f"arxiv-{paper_id.replace('/', '-')}.pdf"
        pdf_path.write_bytes(result.body)
        units = _ingest_pdf(pdf_path)
        abs_url = f"https://arxiv.org/abs/{paper_id}"
        for unit in units:
            unit.source_path = abs_url
        return AssetIngest(
            kind="arxiv", resource_type="paper", title=f"arXiv {paper_id}",
            units=units, source_label=abs_url, fetched_url=pdf_url,
            content_sha256=sha256_bytes(result.body),
            content_bytes=len(result.body),
        )

    if kind == "file":
        from urllib.parse import unquote

        bare = url.split("?")[0].split("#")[0]
        fetch_url = direct_fetch_url(url)
        result = fetch(fetch_url, timeout=max(timeout, 60.0), max_bytes=cap, retries=1)
        if not result.ok:
            raise IngestError(f"could not download {fetch_url} (HTTP {result.status})")
        if len(result.body) >= cap:
            raise IngestError(f"{fetch_url} exceeds the {cap // 1_000_000}MB download cap")
        filename = Path(unquote(bare)).name or "download"
        _check_downloaded_body(filename, result)
        workdir = Path(tempfile.mkdtemp(prefix="aany_dl_"))
        local = workdir / filename
        local.write_bytes(result.body)
        resource_type, units = ingest_file(local)
        for unit in units:
            unit.source_path = url
        return AssetIngest(
            kind="file", resource_type=resource_type,
            title=Path(filename).stem, units=units,
            source_label=url, fetched_url=fetch_url,
            content_sha256=sha256_bytes(result.body),
            content_bytes=len(result.body),
        )

    raise IngestError(f"unsupported asset kind '{kind}' for {url}")


def build_pack_from_cli_tool(name: str, output_dir: str | Path,
                             site_id: str | None = None):
    """Installed software → agent pack (``build cli:<tool>``)."""
    from .ingest_code import ingest_cli_tool

    tool_name, units = ingest_cli_tool(name)
    return _write_units_pack(
        units, "software", site_id or slugify(tool_name, 60) or "tool",
        output_dir, source_label=f"cli:{tool_name}")

def build_pack_from_source(source: str, output_dir: str | Path, site_id: str | None = None):
    """Ingest a local file/directory into a pack. Returns a BuildResult."""
    path = Path(source).expanduser().resolve()
    warnings: list[str] = []
    if path.is_dir():
        resource_type, units, warnings = ingest_directory(path)
        default_id = slugify(path.name, 60)
    else:
        result = ingest_file(path)
        resource_type, units = result
        default_id = slugify(path.stem, 60)
    site_id = site_id or default_id or "resource"
    return _write_units_pack(units, resource_type, site_id, output_dir,
                             source_label=str(path), warnings=warnings)


def unit_manifest(unit: Unit) -> dict:
    """The page-manifest dict for one unit (same schema web pages use)."""
    return {
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


def _write_units_pack(units: list[Unit], resource_type: str, site_id: str,
                      output_dir: str | Path, source_label: str,
                      warnings: list[str] | None = None):
    """Write any list of units as a pack. Shared by every non-web source."""
    from .packer import BuildResult

    warnings = list(warnings or [])
    # surface per-unit ingest warnings stashed in meta (archives do this)
    for unit in units:
        warnings.extend(unit.meta.pop("ingest_warnings", []))

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
        manifest = unit_manifest(unit)
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
        "seed_url": source_label,
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
        "site_name": units[0].title if len(units) == 1 else site_id,
        "resource_type": resource_type,
        "seed_url": source_label,
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
