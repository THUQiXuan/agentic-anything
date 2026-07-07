"""Structured-data sources: CSV/TSV, JSON/JSONL, Jupyter notebooks, SQLite,
email (.eml/.mbox), and RSS/Atom feeds — all standard library."""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from .parser import parse_html
from .util import slugify, truncate_text

_MAX_ROWS_TOTAL = 2000
_ROWS_PER_UNIT = 100
_MAX_JSON_CHARS = 200_000
_MAX_TABLE_SAMPLE = 50
_MAX_MESSAGES = 200
_MAX_FEED_ENTRIES = 200


class DataError(ValueError):
    pass


def _mk_unit(base, index, title, kind, content, path, locator):
    from .ingest import Unit

    return Unit(
        unit_id=f"{base}__{index:03d}__{slugify(title, 40) or 'x'}",
        title=title,
        kind=kind,
        content=content,
        source_path=str(path),
        locator=locator,
    )


# ------------------------------------------------------------- CSV / TSV ---

def ingest_csv(path: Path) -> list:
    from .ingest import _read_text

    text = _read_text(path)
    delimiter = "\t" if path.suffix.lower() == ".tsv" else None
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:8000], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if not rows:
        raise DataError(f"no rows in {path}")
    header, data = rows[0], rows[1:]
    truncated = len(data) > _MAX_ROWS_TOTAL
    data = data[:_MAX_ROWS_TOTAL]
    base = slugify(path.stem, 40)

    overview = [
        {"kind": "heading", "level": 2, "text": f"Table: {path.name}"},
        {"kind": "p", "text": f"{len(data)} data rows"
                              f"{' (truncated)' if truncated else ''}, "
                              f"{len(header)} columns."},
        {"kind": "p", "text": "Columns: " + ", ".join(h.strip() for h in header)},
    ]
    units = [_mk_unit(base, 1, f"{path.name} overview", "table", overview,
                      path, "overview")]
    for start in range(0, len(data), _ROWS_PER_UNIT):
        chunk = data[start:start + _ROWS_PER_UNIT]
        lines = [" | ".join(header)]
        lines += [" | ".join(row) for row in chunk]
        locator = f"rows {start + 1}-{start + len(chunk)}"
        units.append(_mk_unit(
            base, len(units) + 1, f"{path.name} {locator}", "table",
            [{"kind": "p", "text": ln} for ln in lines], path, locator))
    return units


# ------------------------------------------------------------ JSON / JSONL -

def _describe(value, depth=0) -> str:
    if isinstance(value, dict):
        keys = list(value)[:12]
        return "object{" + ", ".join(keys) + (", …" if len(value) > 12 else "") + "}"
    if isinstance(value, list):
        inner = _describe(value[0], depth + 1) if value else "empty"
        return f"array[{len(value)}] of {inner}"
    return type(value).__name__


def ingest_json(path: Path) -> list:
    from .ingest import _read_text

    text = _read_text(path)
    base = slugify(path.stem, 40)

    if path.suffix.lower() == ".jsonl" or _looks_jsonl(text):
        records = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
        if not records:
            raise DataError(f"no valid JSON lines in {path}")
        truncated = len(records) > _MAX_ROWS_TOTAL
        records = records[:_MAX_ROWS_TOTAL]
        overview = [
            {"kind": "heading", "level": 2, "text": f"JSONL: {path.name}"},
            {"kind": "p", "text": f"{len(records)} records"
                                  f"{' (truncated)' if truncated else ''}. "
                                  f"Record shape: {_describe(records[0])}"},
        ]
        units = [_mk_unit(base, 1, f"{path.name} overview", "data", overview,
                          path, "overview")]
        for start in range(0, len(records), _ROWS_PER_UNIT):
            chunk = records[start:start + _ROWS_PER_UNIT]
            body = "\n".join(json.dumps(r, ensure_ascii=False)[:2000] for r in chunk)
            locator = f"records {start + 1}-{start + len(chunk)}"
            units.append(_mk_unit(base, len(units) + 1, f"{path.name} {locator}",
                                  "data", [{"kind": "pre", "text": body}],
                                  path, locator))
        return units

    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise DataError(f"invalid JSON in {path}: {exc}") from exc
    pretty = json.dumps(payload, ensure_ascii=False, indent=2)
    truncated = len(pretty) > _MAX_JSON_CHARS
    pretty = pretty[:_MAX_JSON_CHARS]
    overview = [
        {"kind": "heading", "level": 2, "text": f"JSON: {path.name}"},
        {"kind": "p", "text": f"Top-level shape: {_describe(payload)}"
                              f"{' (content truncated)' if truncated else ''}"},
    ]
    units = [_mk_unit(base, 1, f"{path.name} overview", "data", overview,
                      path, "overview")]
    chunk_size = 12_000
    for i, start in enumerate(range(0, len(pretty), chunk_size), 1):
        units.append(_mk_unit(
            base, len(units) + 1, f"{path.name} part {i}", "data",
            [{"kind": "pre", "text": pretty[start:start + chunk_size],
              "lang": "json"}],
            path, f"part {i}"))
    return units


def _looks_jsonl(text: str) -> bool:
    lines = [ln for ln in text.splitlines()[:5] if ln.strip()]
    if len(lines) < 2:
        return False
    return all(ln.lstrip().startswith(("{", "[")) for ln in lines)


# ------------------------------------------------------------- notebooks ---

def ingest_ipynb(path: Path) -> list:
    from .ingest import _read_text

    try:
        nb = json.loads(_read_text(path))
    except ValueError as exc:
        raise DataError(f"invalid notebook JSON in {path}: {exc}") from exc
    cells = nb.get("cells")
    if not isinstance(cells, list) or not cells:
        raise DataError(f"no cells in notebook {path}")

    lang = (nb.get("metadata", {}).get("kernelspec", {}) or {}).get("language", "python")
    base = slugify(path.stem, 40)
    units = []
    items: list[dict] = []
    title = path.stem

    def flush() -> None:
        nonlocal items, title
        if items:
            index = len(units) + 1
            units.append(_mk_unit(base, index, title, "section", items,
                                  path, f"cells group {index}"))
        items = []

    for cell in cells:
        source = "".join(cell.get("source") or [])
        cell_type = cell.get("cell_type")
        if cell_type == "markdown":
            heading = re.match(r"^(#{1,6})\s+(.+)$", source.strip().splitlines()[0]
                               if source.strip() else "")
            if heading:
                flush()
                title = heading.group(2).strip()
            if source.strip():
                items.append({"kind": "p", "text": source.strip()})
        elif cell_type == "code" and source.strip():
            items.append({"kind": "pre", "text": source.rstrip(), "lang": lang})
            for output in cell.get("outputs") or []:
                text_out = output.get("text") or (
                    (output.get("data") or {}).get("text/plain"))
                if text_out:
                    joined = "".join(text_out) if isinstance(text_out, list) else str(text_out)
                    items.append({"kind": "pre",
                                  "text": "# output:\n" + truncate_text(joined, 1500)})
    flush()
    if not units:
        raise DataError(f"no readable cells in notebook {path}")
    return units


# --------------------------------------------------------------- SQLite ----

def ingest_sqlite(path: Path) -> list:
    from .ingest import Unit

    base = slugify(path.stem, 40)
    uri = f"file:{path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise DataError(f"cannot open SQLite database {path}: {exc}") from exc
    try:
        conn.text_factory = lambda b: b.decode("utf-8", errors="replace")
        cursor = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = cursor.fetchall()
        if not tables:
            raise DataError(f"no tables in {path}")
        units = []
        toc = [{"kind": "heading", "level": 2, "text": f"Database: {path.name}"},
               {"kind": "p", "text": "Tables: " + ", ".join(t[0] for t in tables)}]
        units.append(_mk_unit(base, 1, f"{path.name} overview", "database",
                              toc, path, "overview"))
        for name, ddl in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
                rows = conn.execute(f"SELECT * FROM {quoted} LIMIT {_MAX_TABLE_SAMPLE}")
                columns = [d[0] for d in rows.description]
                sample = rows.fetchall()
            except sqlite3.Error as exc:
                sample, columns, count = [], [], f"error: {exc}"
            content = [{"kind": "heading", "level": 2, "text": f"Table: {name}"},
                       {"kind": "p", "text": f"{count} rows."}]
            if ddl:
                content.append({"kind": "pre", "text": ddl, "lang": "sql"})
            if sample:
                lines = [" | ".join(columns)]
                lines += [" | ".join(truncate_text(str(v), 80) for v in row)
                          for row in sample]
                content.append({"kind": "p",
                                "text": f"First {len(sample)} rows:"})
                content += [{"kind": "p", "text": ln} for ln in lines]
            units.append(_mk_unit(base, len(units) + 1, f"Table: {name}",
                                  "database", content, path, f"table {name}"))
        return units
    finally:
        conn.close()


# ----------------------------------------------------------------- email ---

def _email_unit_content(message) -> list[dict]:
    content: list[dict] = []
    for key in ("From", "To", "Date", "Subject"):
        if message.get(key):
            content.append({"kind": "p", "text": f"{key}: {message.get(key)}"})
    body_text = ""
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                body_text = _decode_part(part)
                break
        else:
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    structure = parse_html(_decode_part(part), "email://body")
                    body_text = "\n".join(b.text for b in structure.blocks)
                    break
    else:
        payload = _decode_part(message)
        if message.get_content_type() == "text/html":
            structure = parse_html(payload, "email://body")
            body_text = "\n".join(b.text for b in structure.blocks)
        else:
            body_text = payload
    for para in re.split(r"\n\s*\n", body_text or ""):
        para = para.strip()
        if para:
            content.append({"kind": "p", "text": truncate_text(para, 4000)})
    return content


def _decode_part(part) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return str(part.get_payload())
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def ingest_eml(path: Path) -> list:
    import email
    import email.policy

    message = email.message_from_bytes(path.read_bytes(),
                                       policy=email.policy.default)
    content = _email_unit_content(message)
    if not content:
        raise DataError(f"empty email {path}")
    subject = message.get("Subject", path.stem) or path.stem
    return [_mk_unit(slugify(path.stem, 40), 1, subject, "email", content,
                     path, "message")]


def ingest_mbox(path: Path) -> list:
    import mailbox

    box = mailbox.mbox(str(path))
    base = slugify(path.stem, 40)
    units = []
    for index, message in enumerate(box, 1):
        if index > _MAX_MESSAGES:
            break
        content = _email_unit_content(message)
        if not content:
            continue
        subject = message.get("Subject", f"message {index}") or f"message {index}"
        units.append(_mk_unit(base, index, subject, "email", content,
                              path, f"message {index}"))
    if not units:
        raise DataError(f"no readable messages in {path}")
    return units


# ------------------------------------------------------------ RSS / Atom ---

_ATOM = "{http://www.w3.org/2005/Atom}"
_RSS1 = "{http://purl.org/rss/1.0/}"
_RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
_DC = "{http://purl.org/dc/elements/1.1/}"


def parse_feed(data: bytes, source_label: str) -> tuple[str, list]:
    """Parse RSS 2.0 / RSS 1.0 (RDF) / Atom bytes → (feed_title, units)."""
    from .ingest import Unit

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise DataError(f"not a valid RSS/Atom feed: {exc}") from exc

    units = []
    if root.tag == "rss" or root.tag.endswith("}rss"):
        channel = root.find("channel")
        feed_title = (channel.findtext("title") or "feed") if channel is not None else "feed"
        entries = channel.findall("item") if channel is not None else []
        get = lambda e, k: e.findtext(k) or ""  # noqa: E731
        get_link = lambda e: e.findtext("link") or ""  # noqa: E731

        def get_body(e):
            return (e.findtext(f"{_CONTENT_NS}encoded")
                    or e.findtext("description") or "")

        get_date = lambda e: e.findtext("pubDate") or ""  # noqa: E731
        get_audio = lambda e: (e.find("enclosure").get("url", "")
                               if e.find("enclosure") is not None else "")  # noqa: E731
    elif root.tag == f"{_RDF}RDF":
        # RSS 1.0: channel and items are namespaced siblings under rdf:RDF
        channel = root.find(f"{_RSS1}channel")
        feed_title = (channel.findtext(f"{_RSS1}title") or "feed") \
            if channel is not None else "feed"
        entries = root.findall(f"{_RSS1}item")
        get = lambda e, k: e.findtext(f"{_RSS1}{k}") or ""  # noqa: E731
        get_link = lambda e: e.findtext(f"{_RSS1}link") or ""  # noqa: E731

        def get_body(e):
            return (e.findtext(f"{_CONTENT_NS}encoded")
                    or e.findtext(f"{_RSS1}description") or "")

        get_date = lambda e: e.findtext(f"{_DC}date") or ""  # noqa: E731
        get_audio = lambda e: ""  # noqa: E731
    elif root.tag == f"{_ATOM}feed":
        feed_title = root.findtext(f"{_ATOM}title") or "feed"
        entries = root.findall(f"{_ATOM}entry")
        get = lambda e, k: e.findtext(f"{_ATOM}{k}") or ""  # noqa: E731

        def get_link(e):
            node = e.find(f"{_ATOM}link")
            return node.get("href", "") if node is not None else ""

        def get_body(e):
            return (e.findtext(f"{_ATOM}content") or
                    e.findtext(f"{_ATOM}summary") or "")

        get_date = lambda e: (e.findtext(f"{_ATOM}updated") or
                              e.findtext(f"{_ATOM}published") or "")  # noqa: E731
        get_audio = lambda e: ""  # noqa: E731
    else:
        raise DataError(f"unrecognized feed root element: {root.tag}")

    base = slugify(feed_title, 40) or "feed"
    for index, entry in enumerate(entries[:_MAX_FEED_ENTRIES], 1):
        entry_title = get(entry, "title") or f"entry {index}"
        body_raw = get_body(entry)
        if "<" in body_raw:  # html body
            structure = parse_html(body_raw, source_label)
            body_paras = [b.text for b in structure.blocks] or [
                re.sub(r"<[^>]+>", " ", body_raw)]
        else:
            body_paras = [body_raw] if body_raw else []
        content = [{"kind": "heading", "level": 2, "text": entry_title}]
        if get_date(entry):
            content.append({"kind": "p", "text": f"date: {get_date(entry)}"})
        if get_link(entry):
            content.append({"kind": "p", "text": f"link: {get_link(entry)}"})
        audio = get_audio(entry)
        if audio:
            content.append({"kind": "p", "text": f"audio enclosure: {audio}"})
        content += [{"kind": "p", "text": truncate_text(p, 4000)}
                    for p in body_paras if p.strip()]
        units.append(Unit(
            unit_id=f"{base}__{index:03d}__{slugify(entry_title, 40) or 'entry'}",
            title=entry_title,
            kind="feed_entry",
            content=content,
            source_path=source_label,
            locator=f"entry {index}",
        ))
    if not units:
        raise DataError("feed has no entries")
    return feed_title, units
