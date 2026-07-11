"""Deterministic read/query layer over an agent-native resource pack.

``PackReader`` gives programmatic access; ``search_pack`` returns ranked units
and matching evidence blocks through structured Unicode BM25F (or the retained
legacy scorer) — no LLM and no network.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .retrieval import BM25FIndex, SearchDocument, analyze, fields_from_manifest
from .util import read_json


class PackNotFound(FileNotFoundError):
    pass


class PackReader:
    def __init__(self, pack_dir: str | Path) -> None:
        self.pack_dir = Path(pack_dir).resolve()
        if not (self.pack_dir / "agent-pack.json").exists():
            raise PackNotFound(
                f"{self.pack_dir} is not an Agentic Anything pack "
                "(missing agent-pack.json). Build one with: "
                "agentic-anything agentify <source> -o <dir>"
            )
        self._discovery: dict | None = None
        self._site: dict | None = None
        self._apis: dict | None = None
        self._pages: dict[str, dict] = {}
        self._retrieval_index: BM25FIndex | None = None

    @property
    def discovery(self) -> dict:
        if self._discovery is None:
            self._discovery = read_json(self.pack_dir / "agent-pack.json")
        return self._discovery

    @property
    def site(self) -> dict:
        if self._site is None:
            self._site = read_json(self.pack_dir / "site.json")
        return self._site

    @property
    def apis(self) -> dict:
        if self._apis is None:
            path = self.pack_dir / "api" / "apis.json"
            self._apis = read_json(path) if path.exists() else {}
        return self._apis

    def page_ids(self) -> list[str]:
        return [p["page_id"] for p in self.site.get("pages", [])]

    def page(self, page_id: str) -> dict:
        if page_id not in self._pages:
            path = self.pack_dir / "pages" / f"{page_id}.json"
            if not path.exists():
                raise PackNotFound(f"page '{page_id}' not found in pack {self.pack_dir}")
            self._pages[page_id] = read_json(path)
        return self._pages[page_id]

    def page_markdown(self, page_id: str) -> str:
        path = self.pack_dir / "pages" / f"{page_id}.md"
        if not path.exists():
            raise PackNotFound(f"page markdown '{page_id}' not found in pack {self.pack_dir}")
        return path.read_text(encoding="utf-8")

    def skill_path(self) -> Path:
        return self.pack_dir / "skills" / "SKILL.md"

    def info(self) -> dict:
        site = self.site
        return {
            "site_id": site.get("site_id"),
            "resource_type": site.get("resource_type") or self.discovery.get("resource_type"),
            "seed_url": site.get("seed_url"),
            "captured_at": site.get("captured_at"),
            "capture_mode": site.get("capture_mode"),
            "page_count": site.get("page_count"),
            "frontier_count": len(site.get("frontier", [])),
            "capabilities": self.discovery.get("capabilities", []),
            "api_surface": {k: len(v) for k, v in self.apis.items() if isinstance(v, list)},
            "has_skill": self.skill_path().exists(),
            "pack_dir": str(self.pack_dir),
        }


_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")

_FIELD_WEIGHTS = {
    "title": 5.0,
    "heading": 3.0,
    "summary": 2.0,
    "block": 1.0,
    "link": 1.5,
    "form": 2.0,
}


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _legacy_search_pack(pack: PackReader | str | Path, query: str, top: int = 5) -> list[dict]:
    """Original v0.3 TF field scorer, retained as an experiment baseline."""
    reader = pack if isinstance(pack, PackReader) else PackReader(pack)
    q_tokens = set(_tokens(query))
    if not q_tokens:
        return []

    results = []
    for page_id in reader.page_ids():
        manifest = reader.page(page_id)
        score = 0.0
        evidence: list[dict] = []

        def score_text(text: str, weight_key: str, kind: str) -> float:
            hits = q_tokens.intersection(_tokens(text))
            if not hits:
                return 0.0
            gained = _FIELD_WEIGHTS[weight_key] * len(hits)
            if len(evidence) < 5:
                evidence.append({"kind": kind, "text": text[:300], "matched": sorted(hits)})
            return gained

        score += score_text(manifest.get("title", ""), "title", "title")
        score += score_text(manifest.get("summary", ""), "summary", "summary")
        for item in manifest.get("content", []):
            key = "heading" if item.get("kind") == "heading" else "block"
            score += score_text(item.get("text", ""), key, item.get("kind", "block"))
        for link in manifest.get("links", []):
            score += score_text(link.get("text", ""), "link", "link")
        for form in manifest.get("forms", []):
            form_text = " ".join(
                [form.get("form_id", "")]
                + [f.get("name", "") + " " + f.get("label", "") for f in form.get("fields", [])]
            )
            score += score_text(form_text, "form", "form")

        if score > 0:
            # Light length normalization so long pages don't always win.
            block_count = max(1, len(manifest.get("content", [])))
            results.append(
                {
                    "page_id": page_id,
                    "url": manifest.get("source_url", ""),
                    "title": manifest.get("title", ""),
                    "score": round(score / math.log2(block_count + 2), 3),
                    "evidence": evidence,
                }
            )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top]


def _hybrid_search_pack(reader: PackReader, query: str, top: int = 5) -> list[dict]:
    if reader._retrieval_index is None:
        documents = [
            SearchDocument(page_id, fields_from_manifest(reader.page(page_id)))
            for page_id in reader.page_ids()
        ]
        reader._retrieval_index = BM25FIndex(documents)
    ranked = reader._retrieval_index.search(query, top=top)
    results: list[dict] = []
    for hit in ranked:
        page_id = hit["doc_id"]
        manifest = reader.page(page_id)
        results.append({
            "page_id": page_id,
            "url": manifest.get("source_url", ""),
            "title": manifest.get("title", ""),
            "score": round(hit["score"], 3),
            "evidence": _evidence(manifest, query),
            "retrieval_method": "bm25f-unicode",
        })
    return results


def _evidence(manifest: dict, query: str) -> list[dict]:
    query_tokens = set(analyze(query))
    candidates: list[tuple[int, int, dict]] = []
    order = 0

    def add(kind: str, text: str) -> None:
        nonlocal order
        if not text:
            return
        snippet = _focused_snippet(text, query_tokens)
        matched = query_tokens.intersection(analyze(snippet))
        if matched:
            candidates.append((-len(matched), order, {
                "kind": kind,
                "text": snippet,
                "matched": sorted({token.split(":", 1)[-1] for token in matched}),
            }))
        order += 1

    add("title", manifest.get("title", ""))
    add("summary", manifest.get("summary", ""))
    for item in manifest.get("content", []):
        add(item.get("kind", "block"), item.get("text", ""))
    for link in manifest.get("links", []):
        add("link", link.get("text", ""))
    for form in manifest.get("forms", []):
        add("form", " ".join(
            [form.get("form_id", "")]
            + [f"{field.get('name', '')} {field.get('label', '')}"
               for field in form.get("fields", [])]
        ))
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in candidates[:5]]


def _focused_snippet(text: str, query_tokens: set[str], limit: int = 300) -> str:
    """Return a short window that actually contains the strongest query match.

    Evidence blocks from PDFs, code files, and tables can contain thousands of
    characters. Taking their first 300 characters hides a match near the end and
    produces a citation that looks unrelated to the query. Candidate windows are
    therefore centered around query terms and ranked by distinct token coverage.
    """
    if len(text) <= limit:
        return text

    normalized = text.casefold()
    positions: list[int] = []
    for token in query_tokens:
        term = token.split(":", 1)[-1]
        if not term:
            continue
        start = 0
        while len(positions) < 200:
            found = normalized.find(term, start)
            if found < 0:
                break
            positions.append(found)
            start = found + max(1, len(term))

    if not positions:
        return text[:limit].rstrip() + "…"

    best: tuple[int, int, int] | None = None
    for position in positions:
        start = max(0, min(len(text) - limit, position - limit // 3))
        window = text[start:start + limit]
        coverage = len(query_tokens.intersection(analyze(window)))
        # Prefer broader query coverage, then the earliest equally good window.
        candidate = (coverage, -start, start)
        if best is None or candidate > best:
            best = candidate

    assert best is not None
    start = best[2]
    snippet = text[start:start + limit].strip()
    if start:
        snippet = "…" + snippet
    if start + limit < len(text):
        snippet += "…"
    return snippet


def search_pack(
    pack: PackReader | str | Path,
    query: str,
    top: int = 5,
    *,
    method: str = "hybrid",
) -> list[dict]:
    """Search a pack with Unicode BM25F (default) or the v0.3 legacy scorer."""
    reader = pack if isinstance(pack, PackReader) else PackReader(pack)
    if method == "hybrid":
        return _hybrid_search_pack(reader, query, top=top)
    if method == "legacy":
        return _legacy_search_pack(reader, query, top=top)
    raise ValueError(f"unknown retrieval method '{method}' (expected hybrid or legacy)")
