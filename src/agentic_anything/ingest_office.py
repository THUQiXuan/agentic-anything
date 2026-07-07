"""Office documents (DOCX / PPTX / XLSX) via stdlib zip + XML only.

OOXML files are zip archives of XML parts; we read the text-bearing parts
directly with ``xml.etree`` — no python-docx/openpyxl dependency.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .util import slugify, truncate_text

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"

_MAX_SHEET_ROWS = 200
_MAX_SLIDE_COUNT = 300


class OfficeError(ValueError):
    pass


def _open_zip(path: Path) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise OfficeError(f"not a valid Office file (bad zip): {path}") from exc


def _read_xml(book: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        return ET.fromstring(book.read(name))
    except (KeyError, ET.ParseError):
        return None


# ----------------------------------------------------------------- DOCX ----

def _strip_fallbacks(root: ET.Element) -> None:
    """Drop mc:Fallback subtrees — they duplicate mc:Choice content."""
    for parent in root.iter():
        for child in list(parent):
            if child.tag == f"{_MC}Fallback":
                parent.remove(child)


def _para_text(para: ET.Element) -> str:
    """Paragraph text with tabs/breaks as separators, skipping nested
    text-box paragraphs (they are walked separately)."""
    parts: list[str] = []

    def walk(node: ET.Element) -> None:
        for child in node:
            if child.tag == f"{_W}txbxContent":
                continue  # nested paragraphs are visited by the main loop
            if child.tag == f"{_W}t":
                parts.append(child.text or "")
            elif child.tag in (f"{_W}tab", f"{_W}br", f"{_W}cr"):
                parts.append(" ")
            else:
                walk(child)

    walk(para)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _docx_heading_map(book: zipfile.ZipFile) -> dict[str, int]:
    """styleId -> outline level, locale-independent (via w:name 'heading N')."""
    mapping: dict[str, int] = {}
    styles = _read_xml(book, "word/styles.xml")
    if styles is None:
        return mapping
    for style in styles.iter(f"{_W}style"):
        style_id = style.get(f"{_W}styleId", "")
        name_node = style.find(f"{_W}name")
        name = name_node.get(f"{_W}val", "") if name_node is not None else ""
        match = re.fullmatch(r"heading (\d)", name.lower())
        if style_id and match:
            mapping[style_id] = int(match.group(1))
    return mapping


def ingest_docx(path: Path) -> list:
    """Word document → sections split on Heading styles (like markdown).

    Handles tabs/line-breaks as separators, tables as pipe-joined rows,
    text boxes without duplication, and localized heading style ids.
    """
    from .ingest import Unit  # late import to avoid a cycle

    with _open_zip(path) as book:
        root = _read_xml(book, "word/document.xml")
        if root is None:
            raise OfficeError(f"no word/document.xml in {path}")
        _strip_fallbacks(root)
        heading_map = _docx_heading_map(book)

        base = slugify(path.stem, 40)
        sections: list[tuple[str, int, list[dict]]] = []
        title, level = path.stem, 0
        items: list[dict] = []

        # Walk block-level elements in document order; tables render as rows.
        parents = {child: parent for parent in root.iter() for child in parent}

        def in_table_or_textbox(node: ET.Element) -> bool:
            current = parents.get(node)
            while current is not None:
                if current.tag in (f"{_W}tbl", f"{_W}txbxContent"):
                    return True
                current = parents.get(current)
            return False

        def heading_level_of(para: ET.Element) -> int:
            style = para.find(f"{_W}pPr/{_W}pStyle")
            style_val = style.get(f"{_W}val", "") if style is not None else ""
            match = re.match(r"(?:Heading|heading)(\d)", style_val or "")
            if match:
                return int(match.group(1))
            if style_val in heading_map:
                return heading_map[style_val]
            outline = para.find(f"{_W}pPr/{_W}outlineLvl")
            if outline is not None:
                try:
                    return int(outline.get(f"{_W}val", "")) + 1
                except ValueError:
                    pass
            return 0

        for node in root.iter():
            if node.tag == f"{_W}tbl":
                if in_table_or_textbox(node):
                    continue  # nested tables handled with their parent
                for row in node.iter(f"{_W}tr"):
                    cells = [
                        " ".join(filter(None, (_para_text(p)
                                               for p in cell.iter(f"{_W}p"))))
                        for cell in row.findall(f"{_W}tc")
                    ]
                    line = " | ".join(cells).strip(" |")
                    if line:
                        items.append({"kind": "p", "text": line})
                continue
            if node.tag != f"{_W}p" or in_table_or_textbox(node):
                continue
            text = _para_text(node)
            if not text:
                continue
            heading = heading_level_of(node)
            if heading:
                sections.append((title, level, items))
                title, level = text, heading
                items = [{"kind": "heading", "level": heading, "text": text}]
            else:
                items.append({"kind": "p", "text": text})

        # text-box paragraphs, once, at the end of their section stream
        for box in root.iter(f"{_W}txbxContent"):
            for para in box.iter(f"{_W}p"):
                text = _para_text(para)
                if text:
                    items.append({"kind": "p", "text": text})
        sections.append((title, level, items))

    units = []
    for section_title, _section_level, section_items in sections:
        if not section_items and len(sections) > 1:
            continue
        index = len(units) + 1
        units.append(Unit(
            unit_id=f"{base}__{index:03d}__{slugify(section_title, 40) or 'x'}",
            title=section_title,
            kind="section",
            content=section_items,
            source_path=str(path),
            locator=f"section {index}",
        ))
    if not units:
        raise OfficeError(f"no readable text in {path}")
    return units


# ----------------------------------------------------------------- PPTX ----

def ingest_pptx(path: Path) -> list:
    """Presentation → one unit per slide (title = first text line)."""
    from .ingest import Unit

    with _open_zip(path) as book:
        slide_names = sorted(
            (n for n in book.namelist()
             if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n).group(1)),
        )[:_MAX_SLIDE_COUNT]
        if not slide_names:
            raise OfficeError(f"no slides found in {path}")

        base = slugify(path.stem, 40)
        units = []
        for index, name in enumerate(slide_names, 1):
            root = _read_xml(book, name)
            if root is None:
                continue
            lines: list[str] = []
            # a:p paragraphs inside shapes; a:br is a line break separator
            for para in root.iter(f"{_A}p"):
                parts: list[str] = []
                for node in para.iter():
                    if node.tag == f"{_A}t":
                        parts.append(node.text or "")
                    elif node.tag == f"{_A}br":
                        parts.append(" ")
                text = re.sub(r"\s+", " ", "".join(parts)).strip()
                if text:
                    lines.append(text)
            if not lines:
                continue
            slide_title = truncate_text(lines[0], 80)
            content = [{"kind": "heading", "level": 2, "text": slide_title}]
            content += [{"kind": "p", "text": ln} for ln in lines[1:]]
            units.append(Unit(
                unit_id=f"{base}__slide{index:03d}",
                title=f"Slide {index}: {slide_title}",
                kind="slide",
                content=content,
                source_path=str(path),
                locator=f"slide {index}",
            ))
    if not units:
        raise OfficeError(f"no readable text on any slide in {path}")
    return units


# ----------------------------------------------------------------- XLSX ----

def _column_of(cell_ref: str) -> int:
    col = 0
    for ch in cell_ref:
        if ch.isalpha():
            col = col * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return col


_DATE_NUMFMT_IDS = set(range(14, 23)) | set(range(45, 48))


def _xlsx_date_styles(book: zipfile.ZipFile) -> set[int]:
    """Indices (s= attribute values) of cell styles with builtin date formats."""
    styles = _read_xml(book, "xl/styles.xml")
    if styles is None:
        return set()
    date_styles: set[int] = set()
    xfs = styles.find(f"{_S}cellXfs")
    if xfs is None:
        return set()
    for index, xf in enumerate(xfs.findall(f"{_S}xf")):
        try:
            if int(xf.get("numFmtId", "0")) in _DATE_NUMFMT_IDS:
                date_styles.add(index)
        except ValueError:
            continue
    return date_styles


def _excel_serial_to_iso(raw: str) -> str:
    from datetime import date, timedelta

    try:
        serial = float(raw)
    except ValueError:
        return raw
    if not 1 <= serial < 300000:
        return raw
    day = date(1899, 12, 30) + timedelta(days=int(serial))
    return day.isoformat()


def _shared_string(si: ET.Element) -> str:
    """Direct + rich-run text only; phonetic <rPh> furigana is excluded."""
    parts = [t.text or "" for t in si.findall(f"{_S}t")]
    for run in si.findall(f"{_S}r"):
        parts.extend(t.text or "" for t in run.findall(f"{_S}t"))
    return "".join(parts)


def ingest_xlsx(path: Path) -> list:
    """Workbook → one unit per sheet, rows rendered as pipe-separated lines."""
    from .ingest import Unit

    with _open_zip(path) as book:
        shared: list[str] = []
        strings_root = _read_xml(book, "xl/sharedStrings.xml")
        if strings_root is not None:
            for si in strings_root.iter(f"{_S}si"):
                shared.append(_shared_string(si))
        date_styles = _xlsx_date_styles(book)

        workbook_root = _read_xml(book, "xl/workbook.xml")
        sheet_names: list[str] = []
        if workbook_root is not None:
            for sheet in workbook_root.iter(f"{_S}sheet"):
                sheet_names.append(sheet.get("name", f"Sheet{len(sheet_names) + 1}"))

        sheet_files = sorted(
            (n for n in book.namelist()
             if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n).group(1)),
        )
        if not sheet_files:
            raise OfficeError(f"no worksheets found in {path}")

        base = slugify(path.stem, 40)
        units = []
        for index, name in enumerate(sheet_files, 1):
            root = _read_xml(book, name)
            if root is None:
                continue
            rows_out: list[str] = []
            truncated = False
            for row in root.iter(f"{_S}row"):
                if len(rows_out) >= _MAX_SHEET_ROWS:
                    truncated = True
                    break
                cells: dict[int, str] = {}
                last_col = 0
                for cell in row.iter(f"{_S}c"):
                    # r= is optional; r-less cells are positioned sequentially
                    col = _column_of(cell.get("r", "")) or (last_col + 1)
                    last_col = col
                    cell_type = cell.get("t", "")
                    value_node = cell.find(f"{_S}v")
                    if value_node is None or value_node.text is None:
                        inline = cell.find(f"{_S}is")
                        if inline is not None:
                            cells[col] = _shared_string(inline)
                        continue
                    raw = value_node.text
                    if cell_type == "s":  # shared-string index
                        try:
                            raw = shared[int(raw)]
                        except (ValueError, IndexError):
                            pass
                    elif cell_type == "b":
                        raw = "TRUE" if raw == "1" else "FALSE"
                    elif not cell_type:
                        try:
                            if int(cell.get("s", "-1")) in date_styles:
                                raw = _excel_serial_to_iso(raw)
                        except ValueError:
                            pass
                    cells[col] = raw
                if cells:
                    width = max(cells)
                    rows_out.append(" | ".join(
                        cells.get(i, "") for i in range(1, width + 1)))
            if not rows_out:
                continue
            sheet_name = (sheet_names[index - 1]
                          if index - 1 < len(sheet_names) else f"Sheet{index}")
            content = [{"kind": "heading", "level": 2,
                        "text": f"Sheet: {sheet_name}"}]
            content += [{"kind": "p", "text": line} for line in rows_out]
            if truncated:
                content.append({"kind": "p",
                                "text": f"(truncated at {_MAX_SHEET_ROWS} rows)"})
            units.append(Unit(
                unit_id=f"{base}__{index:03d}__{slugify(sheet_name, 40) or 'sheet'}",
                title=f"Sheet: {sheet_name}",
                kind="sheet",
                content=content,
                source_path=str(path),
                locator=f"sheet '{sheet_name}'",
            ))
    if not units:
        raise OfficeError(f"no readable cells in {path}")
    return units
