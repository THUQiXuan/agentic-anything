"""Structured HTML extraction using only the standard library.

Produces a ``PageStructure`` with title, meta description, headings,
content blocks, links, images, forms, JSON-LD payloads, script references,
and feed/iframe hints — the non-visual representation agents read instead
of raw HTML.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

_BLOCK_TAGS = {
    "p", "li", "td", "th", "dt", "dd", "figcaption", "blockquote", "pre", "summary",
}
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
# Block-level containers whose start implicitly terminates an open <p>/<li>/...
_BLOCK_BREAKERS = {
    "div", "section", "article", "main", "header", "footer", "aside",
    "table", "ul", "ol", "dl", "form", "nav", "figure", "fieldset", "hr",
}


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class Block:
    kind: str
    text: str


@dataclass
class Link:
    text: str
    href: str
    url: str  # absolute
    rel: str = ""
    is_nav: bool = False


@dataclass
class Image:
    src: str
    url: str
    alt: str = ""


@dataclass
class FormField:
    name: str
    input_type: str = "text"
    label: str = ""
    required: bool = False
    placeholder: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class Form:
    form_id: str
    action: str
    action_url: str
    method: str = "GET"
    fields: list[FormField] = field(default_factory=list)
    submit_labels: list[str] = field(default_factory=list)


@dataclass
class PageStructure:
    title: str = ""
    meta_description: str = ""
    lang: str = ""
    canonical_url: str = ""
    headings: list[Heading] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    # Document-order stream of headings and blocks:
    # {"kind": "heading", "level": n, "text": ...} or {"kind": "p"|"li"|..., "text": ...}
    content: list[dict] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)
    forms: list[Form] = field(default_factory=list)
    json_ld: list[dict] = field(default_factory=list)
    script_srcs: list[str] = field(default_factory=list)
    inline_scripts: list[str] = field(default_factory=list)
    feeds: list[dict] = field(default_factory=list)
    iframes: list[str] = field(default_factory=list)
    refresh_url: str = ""  # <meta http-equiv="refresh" content="0;url=...">, resolved

    def text_summary(self, limit: int = 240) -> str:
        parts: list[str] = []
        if self.headings:
            parts.append(self.headings[0].text)
        for block in self.blocks:
            if block.text and block.text not in parts:
                parts.append(block.text)
                break
        summary = " — ".join(p for p in parts if p)
        return summary[:limit]


class _StructParser(HTMLParser):
    """Single-pass extractor. Tracks a small stack of open contexts."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.out = PageStructure()
        self._skip_depth = 0
        self._in_title = False
        self._heading_level = 0
        self._heading_buf: list[str] = []
        self._block_tag: str | None = None
        self._block_buf: list[str] = []
        self._loose_buf: list[str] = []  # text outside any known block context
        self._link_stack: list[dict] = []
        self._nav_depth = 0
        self._form: Form | None = None
        self._form_count = 0
        self._select_field: FormField | None = None
        self._in_option = False
        self._option_buf: list[str] = []
        self._label_for: str | None = None
        self._label_buf: list[str] = []
        self._pending_labels: dict[str, str] = {}
        self._fields_by_id: dict[str, FormField] = {}
        self._button_buf: list[str] | None = None
        self._script_kind: str | None = None
        self._script_buf: list[str] = []
        self._in_textarea = False
        self._base_seen = False

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _absolute(self, href: str) -> str:
        try:
            return urljoin(self.base_url, href.strip())
        except ValueError:
            return href

    # -- tag handlers ------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        if tag in _SKIP_TAGS:
            if tag == "script":
                src = attr.get("src", "")
                if src:
                    self.out.script_srcs.append(self._absolute(src))
                    self._script_kind = None
                else:
                    stype = attr.get("type", "").lower()
                    if "ld+json" in stype:
                        self._script_kind = "json_ld"
                    elif stype in ("", "text/javascript", "module", "application/javascript"):
                        self._script_kind = "js"
                    else:
                        self._script_kind = None
                    self._script_buf = []
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag in _BLOCK_BREAKERS:  # implicit close of any open <p>/<li>/...
            self._flush_block()
            self._flush_loose()
        elif tag in _BLOCK_TAGS or tag in _HEADING_TAGS:
            self._flush_loose()

        if tag == "html":
            self.out.lang = attr.get("lang", "")
        elif tag == "base":
            href = attr.get("href", "")
            if href and not self._base_seen:  # first <base> wins, per HTML spec
                self._base_seen = True
                self.base_url = self._absolute(href)
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attr.get("name", "").lower()
            if name == "description":
                self.out.meta_description = self._clean(attr.get("content", ""))
            elif attr.get("http-equiv", "").lower() == "refresh":
                match = re.search(r"url\s*=\s*['\"]?([^'\"\s;]+)", attr.get("content", ""), re.IGNORECASE)
                if match:
                    self.out.refresh_url = self._absolute(match.group(1))
        elif tag == "link":
            rel = attr.get("rel", "").lower()
            href = attr.get("href", "")
            ltype = attr.get("type", "").lower()
            if rel == "canonical" and href:
                self.out.canonical_url = self._absolute(href)
            elif rel == "alternate" and href and ("rss" in ltype or "atom" in ltype or "json" in ltype):
                self.out.feeds.append(
                    {"url": self._absolute(href), "type": ltype, "title": attr.get("title", "")}
                )
        elif tag == "nav":
            self._nav_depth += 1
        elif tag in _HEADING_TAGS:
            self._flush_block()
            self._heading_level = int(tag[1])
            self._heading_buf = []
        elif tag in _BLOCK_TAGS:
            self._flush_block()
            self._block_tag = tag
            self._block_buf = []
        elif tag == "a":
            href = attr.get("href", "")
            self._link_stack.append(
                {
                    "href": href,
                    "rel": attr.get("rel", ""),
                    "text": [],
                    "is_nav": self._nav_depth > 0,
                }
            )
        elif tag == "img":
            src = attr.get("src", "") or attr.get("data-src", "")
            if src:
                image = Image(src=src, url=self._absolute(src), alt=self._clean(attr.get("alt", "")))
                self.out.images.append(image)
                if self._link_stack:
                    self._link_stack[-1]["text"].append(image.alt)
        elif tag == "iframe":
            src = attr.get("src", "")
            if src:
                self.out.iframes.append(self._absolute(src))
        elif tag == "form":
            self._form_count += 1
            action = attr.get("action", "")
            self._form = Form(
                form_id=attr.get("id", "") or f"form-{self._form_count}",
                action=action,
                action_url=self._absolute(action) if action else self.base_url,
                method=(attr.get("method", "") or "GET").upper(),
            )
            self._fields_by_id = {}
        elif tag == "label":
            self._label_for = attr.get("for", "")
            self._label_buf = []
        elif tag == "option":
            self._in_option = True
            self._option_buf = []
        elif tag in ("input", "textarea", "select", "button"):
            self._handle_field(tag, attr)

    def _handle_field(self, tag: str, attr: dict[str, str]) -> None:
        if tag == "button":
            btype = attr.get("type", "submit").lower()
            if btype == "submit" and self._form is not None:
                self._button_buf = []
            return
        if self._form is None:
            return
        name = attr.get("name", "") or attr.get("id", "")
        if tag == "input":
            itype = attr.get("type", "text").lower()
            if itype in ("submit", "button", "image"):
                label = self._clean(attr.get("value", ""))
                if label:
                    self._form.submit_labels.append(label)
                return
            if itype == "hidden" and not name:
                return
            field_obj = FormField(
                name=name,
                input_type=itype,
                required="required" in attr,
                placeholder=self._clean(attr.get("placeholder", "")),
            )
            self._attach_label(field_obj, attr)
            self._form.fields.append(field_obj)
        elif tag == "textarea":
            self._in_textarea = True
            field_obj = FormField(
                name=name,
                input_type="textarea",
                required="required" in attr,
                placeholder=self._clean(attr.get("placeholder", "")),
            )
            self._attach_label(field_obj, attr)
            self._form.fields.append(field_obj)
        elif tag == "select":
            field_obj = FormField(name=name, input_type="select", required="required" in attr)
            self._attach_label(field_obj, attr)
            self._form.fields.append(field_obj)
            self._select_field = field_obj

    def _attach_label(self, field_obj: FormField, attr: dict[str, str]) -> None:
        fid = attr.get("id", "")
        if fid:
            self._fields_by_id[fid] = field_obj
            if fid in self._pending_labels:
                field_obj.label = self._pending_labels.pop(fid)

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            if tag == "script" and self._script_kind:
                payload = "".join(self._script_buf).strip()
                if payload:
                    if self._script_kind == "json_ld":
                        try:
                            parsed = json.loads(payload)
                            items = parsed if isinstance(parsed, list) else [parsed]
                            self.out.json_ld.extend(x for x in items if isinstance(x, dict))
                        except (ValueError, RecursionError):
                            pass
                    else:
                        self.out.inline_scripts.append(payload[:200_000])
                self._script_kind = None
                self._script_buf = []
            return
        if self._skip_depth:
            return

        if tag in _BLOCK_BREAKERS:
            self._flush_loose()

        if tag == "title":
            self._in_title = False
        elif tag == "nav":
            self._nav_depth = max(0, self._nav_depth - 1)
        elif tag in _HEADING_TAGS and self._heading_level:
            text = self._clean("".join(self._heading_buf))
            if text:
                self.out.headings.append(Heading(level=self._heading_level, text=text))
                self.out.content.append(
                    {"kind": "heading", "level": self._heading_level, "text": text}
                )
            self._heading_level = 0
        elif tag in _BLOCK_TAGS and self._block_tag == tag:
            self._flush_block()
        elif tag == "a" and self._link_stack:
            entry = self._link_stack.pop()
            text = self._clean(" ".join(t for t in entry["text"] if t))
            href = entry["href"]
            if href and not href.lower().startswith(("javascript:", "data:")):
                self.out.links.append(
                    Link(
                        text=text,
                        href=href,
                        url=self._absolute(href),
                        rel=entry["rel"],
                        is_nav=entry["is_nav"],
                    )
                )
        elif tag == "form" and self._form is not None:
            self.out.forms.append(self._form)
            self._form = None
            self._select_field = None
        elif tag == "textarea":
            self._in_textarea = False
        elif tag == "select":
            self._select_field = None
        elif tag == "option":
            self._in_option = False
            if self._select_field is not None:
                text = self._clean("".join(self._option_buf))
                if text:
                    self._select_field.options.append(text)
            self._option_buf = []
        elif tag == "label":
            text = self._clean("".join(self._label_buf))
            if self._label_for and text:
                # 'for' references a field id; attach if seen, else store.
                field_obj = self._fields_by_id.get(self._label_for)
                if field_obj is not None and not field_obj.label:
                    field_obj.label = text
                else:
                    self._pending_labels[self._label_for] = text
            self._label_for = None
            self._label_buf = []
        elif tag == "button" and self._button_buf is not None:
            label = self._clean("".join(self._button_buf))
            if label and self._form is not None:
                self._form.submit_labels.append(label)
            self._button_buf = None

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS and tag not in _SKIP_TAGS:
            self.handle_endtag(tag)
        elif tag in _SKIP_TAGS:
            # self-closing script/style: undo the skip-depth bump
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._script_kind is not None and self._skip_depth:
            self._script_buf.append(data)
            return
        if self._skip_depth:
            return
        if self._in_textarea:
            return  # textarea default content is not page text
        claimed = False
        if self._in_title:
            self.out.title += data
            claimed = True
        if self._heading_level:
            self._heading_buf.append(data)
            claimed = True
        if self._block_tag:
            self._block_buf.append(data)
            claimed = True
        if self._link_stack:
            self._link_stack[-1]["text"].append(data)
            claimed = True
        if self._in_option:
            self._option_buf.append(data)
            claimed = True
        if self._label_for is not None:
            self._label_buf.append(data)
            claimed = True
        if self._button_buf is not None:
            self._button_buf.append(data)
            claimed = True
        if not claimed:
            # Bare text in <div>/<span>/<small>/... — collected so content
            # marked up without semantic tags is not lost.
            self._loose_buf.append(data)

    def _flush_block(self) -> None:
        if self._block_tag is None:
            return
        text = self._clean("".join(self._block_buf))
        if text and len(text) > 1:
            self.out.blocks.append(Block(kind=self._block_tag, text=text))
            self.out.content.append({"kind": self._block_tag, "text": text})
        self._block_tag = None
        self._block_buf = []

    def _flush_loose(self) -> None:
        if not self._loose_buf:
            return
        text = self._clean("".join(self._loose_buf))
        self._loose_buf = []
        if text and len(text) > 2:
            self.out.blocks.append(Block(kind="text", text=text))
            self.out.content.append({"kind": "text", "text": text})


def parse_html(html: str, base_url: str) -> PageStructure:
    parser = _StructParser(base_url)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed HTML should never crash a build; keep what we parsed.
        pass
    try:
        parser._flush_block()  # unclosed trailing block at EOF
        parser._flush_loose()
    except Exception:
        pass
    out = parser.out
    out.title = re.sub(r"\s+", " ", out.title).strip()
    return out
