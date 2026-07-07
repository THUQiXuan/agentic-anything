"""Build a site pack: capture + distill a website into agent-native artifacts.

Pack layout::

    <out>/<site-slug>/
      agent-pack.json        discovery document (index of everything below)
      site.json              crawl snapshot: pages, frontier, stats, config
      pages/<page_id>.json   structured page manifest
      pages/<page_id>.md     markdown view of the same page
      html/<page_id>.html    captured HTML evidence (optional)
      snapshots/<page_id>.png  full-page screenshots (optional, render mode)
      api/apis.json          discovered API surface
      skills/SKILL.md        agent skill (added by `skill` command)
      cli/<slug>_cli.py      generated site CLI (added by `clify` command)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import __version__ as VERSION
from .apis import ApiCollector
from .config import BuildConfig
from .crawler import CrawledPage, crawl
from .markdown import page_to_markdown
from .util import (
    page_id_from_url,
    with_default_scheme,
    sha256_bytes,
    site_slug_from_url,
    truncate_text,
    url_path_of,
    utc_now_iso,
    write_json,
)

SPEC_VERSION = "0.1"

_PAGE_TYPE_HINTS = [
    ("pricing", "pricing"),
    ("contact", "contact"),
    ("about", "about"),
    ("login", "auth"),
    ("signin", "auth"),
    ("signup", "auth"),
    ("register", "auth"),
    ("docs", "docs"),
    ("documentation", "docs"),
    ("api", "docs"),
    ("blog", "blog"),
    ("news", "blog"),
    ("faq", "faq"),
    ("help", "faq"),
    ("search", "search"),
    ("cart", "commerce"),
    ("checkout", "commerce"),
    ("product", "commerce"),
    ("shop", "commerce"),
]


def infer_page_type(url_path: str, title: str) -> str:
    haystack = f"{url_path} {title}".lower()
    for needle, ptype in _PAGE_TYPE_HINTS:
        if needle in haystack:
            return ptype
    if url_path in ("/", ""):
        return "landing"
    return "content"


@dataclass
class BuildResult:
    pack_dir: Path
    site_id: str
    page_count: int
    frontier_count: int
    api_count: int
    warnings: list[str]

    def as_json(self) -> dict:
        return {
            "pack_dir": str(self.pack_dir),
            "site_id": self.site_id,
            "page_count": self.page_count,
            "frontier_count": self.frontier_count,
            "api_count": self.api_count,
            "warnings": self.warnings,
        }


def build_pack(
    url: str,
    output_dir: str | Path,
    config: BuildConfig | None = None,
    site_id: str | None = None,
    progress=None,
) -> BuildResult:
    """Capture ``url`` and write a site pack under ``output_dir``.

    ``output_dir`` is the pack directory itself (files are written directly
    into it, so pass e.g. ``packs/example-com``).
    """
    config = config or BuildConfig()
    url = with_default_scheme(url)
    site_id = site_id or site_slug_from_url(url)
    pack_dir = Path(output_dir).resolve()
    pack_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    started = utc_now_iso()

    collector = ApiCollector(url, config)
    sitemap_urls = collector.probe_sitemap()

    renderer_ctx = None
    if config.render:
        from .renderer import Renderer

        renderer_ctx = Renderer(
            timeout_ms=int(config.timeout * 1000),
            render_wait_ms=config.render_wait_ms,
        )

    if renderer_ctx is not None:
        with renderer_ctx as renderer:
            outcome = crawl(url, config, renderer=renderer, sitemap_urls=sitemap_urls, progress=progress)
    else:
        outcome = crawl(url, config, renderer=None, sitemap_urls=sitemap_urls, progress=progress)

    if not outcome.pages:
        warnings.append("no pages captured; check the URL, network access, or robots policy")

    # ---- API surface -------------------------------------------------------
    script_urls: list[str] = []
    for page in outcome.pages:
        collector.collect_from_page(page.page_id, page.final_url, page.structure)
        script_urls.extend(page.structure.script_srcs)
        if page.network_log:
            for entry in page.network_log:
                entry["page_id"] = page.page_id
            collector.collect_network_log(page.network_log)
    collector.collect_external_js(script_urls)
    collector.probe_well_known()

    # ---- per-page artifacts --------------------------------------------------
    captured_ids = {p.page_id for p in outcome.pages}
    page_index: list[dict] = []
    for page in outcome.pages:
        manifest = _page_manifest(page, captured_ids, config)
        write_json(pack_dir / "pages" / f"{page.page_id}.json", manifest)
        md = page_to_markdown(manifest)
        (pack_dir / "pages").mkdir(parents=True, exist_ok=True)
        (pack_dir / "pages" / f"{page.page_id}.md").write_text(md, encoding="utf-8")
        if config.include_html:
            html_dir = pack_dir / "html"
            html_dir.mkdir(parents=True, exist_ok=True)
            (html_dir / f"{page.page_id}.html").write_text(page.html, encoding="utf-8")
        if page.screenshot:
            snap_dir = pack_dir / "snapshots"
            snap_dir.mkdir(parents=True, exist_ok=True)
            (snap_dir / f"{page.page_id}.png").write_bytes(page.screenshot)
        page_index.append(
            {
                "page_id": page.page_id,
                "url": page.final_url,
                "url_path": url_path_of(page.final_url),
                "title": page.structure.title,
                "page_type": manifest["page_type"],
                "summary": manifest["summary"],
                "outgoing_page_ids": manifest["outgoing_page_ids"],
                "form_count": len(page.structure.forms),
                "discovered_via": page.discovered_via,
                "depth": page.depth,
                "rendered": page.rendered,
                "has_screenshot": bool(page.screenshot),
            }
        )

    # ---- site.json ----------------------------------------------------------
    site_snapshot = {
        "spec_version": SPEC_VERSION,
        "generator": f"agentic-anything/{VERSION}",
        "site_id": site_id,
        "seed_url": url,
        "captured_at": started,
        "finished_at": utc_now_iso(),
        "capture_mode": "rendered" if config.render else "static",
        "respect_robots": config.respect_robots,
        "same_origin_only": config.same_origin_only,
        "max_pages": config.max_pages,
        "page_count": len(outcome.pages),
        "pages": page_index,
        "frontier": [
            {
                "url": f.url,
                "candidate_page_id": f.candidate_page_id,
                "skip_reason": f.skip_reason,
                "discovered_via": f.discovered_via,
                "from_page_id": f.from_page_id,
            }
            for f in outcome.frontier
        ],
        "notes": outcome.notes + warnings,
    }
    write_json(pack_dir / "site.json", site_snapshot)
    write_json(pack_dir / "api" / "apis.json", collector.surface.as_json())

    # ---- discovery document ---------------------------------------------------
    capabilities = ["site_snapshot", "page_index", "page_manifests", "markdown_views", "api_surface"]
    if config.include_html:
        capabilities.append("html_evidence")
    if any(p.screenshot for p in outcome.pages):
        capabilities.append("visual_snapshots")
    if collector.surface.observed_network:
        capabilities.append("observed_network_api")
    discovery = {
        "spec_version": SPEC_VERSION,
        "kind": "agentic-anything-pack",
        "site_id": site_id,
        "site_name": (outcome.pages[0].structure.title if outcome.pages else site_id),
        "seed_url": url,
        "generated_at": started,
        "generator": f"agentic-anything/{VERSION}",
        "capabilities": capabilities,
        "contents": {
            "site_snapshot": "site.json",
            "page_manifests": "pages/*.json",
            "markdown_views": "pages/*.md",
            "html_evidence": "html/*.html" if config.include_html else None,
            "visual_snapshots": "snapshots/*.png" if any(p.screenshot for p in outcome.pages) else None,
            "api_surface": "api/apis.json",
            "skill": "skills/SKILL.md",
            "site_cli": f"cli/{site_id.replace('-', '_')}_cli.py",
        },
    }
    discovery["contents"] = {k: v for k, v in discovery["contents"].items() if v}
    write_json(pack_dir / "agent-pack.json", discovery)

    return BuildResult(
        pack_dir=pack_dir,
        site_id=site_id,
        page_count=len(outcome.pages),
        frontier_count=len(outcome.frontier),
        api_count=collector.surface.total,
        warnings=warnings,
    )


def _page_manifest(page: CrawledPage, captured_ids: set[str], config: BuildConfig) -> dict:
    s = page.structure
    links = []
    for link in s.links:
        target_id = page_id_from_url(link.url)
        links.append(
            {
                "text": link.text,
                "url": link.url,
                "target_page_id": target_id if target_id in captured_ids else None,
                "is_nav": link.is_nav,
            }
        )
    manifest = {
        "spec_version": SPEC_VERSION,
        "page_id": page.page_id,
        "source_url": page.final_url,
        "url_path": url_path_of(page.final_url),
        "title": s.title,
        "lang": s.lang,
        "meta_description": s.meta_description,
        "page_type": infer_page_type(url_path_of(page.final_url), s.title),
        "summary": truncate_text(s.text_summary(), 240),
        "content": s.content,
        "links": links,
        "outgoing_page_ids": sorted(
            {l["target_page_id"] for l in links if l["target_page_id"] and l["target_page_id"] != page.page_id}
        ),
        "forms": [
            {
                "form_id": f.form_id,
                "method": f.method,
                "action": f.action,
                "action_url": f.action_url,
                "fields": [
                    {
                        "name": ff.name,
                        "input_type": ff.input_type,
                        "label": ff.label,
                        "required": ff.required,
                        "placeholder": ff.placeholder,
                        "options": ff.options,
                    }
                    for ff in f.fields
                ],
                "submit_labels": f.submit_labels,
            }
            for f in s.forms
        ],
        "images": [{"url": i.url, "alt": i.alt} for i in s.images],
        "json_ld_types": sorted(
            {str(d.get("@type")) for d in s.json_ld if isinstance(d.get("@type"), str)}
        ),
        "provenance": {
            "requested_url": page.url,
            "final_url": page.final_url,
            "http_status": page.status,
            "redirect_chain": page.redirect_chain,
            "capture_mode": "rendered" if page.rendered else "static",
            "discovered_via": page.discovered_via,
            "depth": page.depth,
            "content_sha256": sha256_bytes(page.html.encode("utf-8", errors="replace")),
            "html_path": f"html/{page.page_id}.html" if config.include_html else None,
        },
    }
    if page.screenshot:
        manifest["snapshot_path"] = f"snapshots/{page.page_id}.png"
    return manifest
