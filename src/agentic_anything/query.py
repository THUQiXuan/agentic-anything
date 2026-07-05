"""Deterministic read/query layer over a built site pack.

``PackReader`` gives programmatic access; ``search_pack`` is a lightweight
keyword search (TF scoring with field weights) that returns pages with the
matching evidence blocks — no LLM, no network.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .util import read_json


class PackNotFound(FileNotFoundError):
    pass


class PackReader:
    def __init__(self, pack_dir: str | Path) -> None:
        self.pack_dir = Path(pack_dir).resolve()
        if not (self.pack_dir / "agent-pack.json").exists():
            raise PackNotFound(
                f"{self.pack_dir} is not a site pack (missing agent-pack.json). "
                "Build one with: agentic-anything build <url> -o <dir>"
            )
        self._discovery: dict | None = None
        self._site: dict | None = None
        self._apis: dict | None = None
        self._pages: dict[str, dict] = {}

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


def search_pack(pack: PackReader | str | Path, query: str, top: int = 5) -> list[dict]:
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
