"""API surface discovery.

Aggregates every machine-usable interface a site exposes, from several
independent sources:

- HTML forms (method + action + typed fields)
- API-looking hyperlinks (``/api/``, ``.json``, ``/graphql``, ...)
- ``fetch(...)`` / ``axios`` / ``XMLHttpRequest`` URL literals in inline and
  same-origin external JavaScript (bounded scan)
- Well-known documents: ``openapi.json`` / ``swagger.json``,
  ``/.well-known/ai-plugin.json``, ``/.well-known/agent-site.json``,
  ``sitemap.xml``, ``robots.txt``, RSS/Atom feeds
- Live network requests observed while rendering (Playwright mode)

The result is written to ``api/apis.json`` in the pack and is the main
input for skill generation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import unescape
from urllib.parse import urljoin, urlsplit

from .config import BuildConfig
from .fetcher import fetch
from .parser import PageStructure
from .util import normalize_url, same_origin, same_site

# URL literals inside JS that look like API calls.
_JS_CALL_RE = re.compile(
    r"""(?:fetch|axios\.(?:get|post|put|delete|patch)|\.open)\s*\(\s*['"`]([^'"`\s]{2,300})['"`]""",
    re.IGNORECASE,
)
_JS_URL_RE = re.compile(r"""['"`](/(?:api|rest|graphql|v\d+)/[^'"`\s]{0,200})['"`]""")
_API_PATH_RE = re.compile(r"(/api/|/graphql|/rest/|/v\d+/|\.json($|\?))", re.IGNORECASE)

_OPENAPI_PROBES = [
    "/openapi.json",
    "/swagger.json",
    "/api/openapi.json",
    "/api-docs",
    "/.well-known/openapi.json",
]
_WELL_KNOWN_PROBES = [
    "/.well-known/ai-plugin.json",
    "/.well-known/agent-site.json",
    "/.well-known/mcp.json",
    "/.well-known/security.txt",
]


@dataclass
class ApiSurface:
    endpoints: list[dict] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)
    openapi: list[dict] = field(default_factory=list)
    well_known: list[dict] = field(default_factory=list)
    feeds: list[dict] = field(default_factory=list)
    sitemaps: list[dict] = field(default_factory=list)
    observed_network: list[dict] = field(default_factory=list)

    def as_json(self) -> dict:
        return {
            "endpoints": self.endpoints,
            "forms": self.forms,
            "openapi": self.openapi,
            "well_known": self.well_known,
            "feeds": self.feeds,
            "sitemaps": self.sitemaps,
            "observed_network": self.observed_network,
        }

    @property
    def total(self) -> int:
        return (
            len(self.endpoints)
            + len(self.forms)
            + len(self.openapi)
            + len(self.feeds)
            + len(self.observed_network)
        )


class ApiCollector:
    def __init__(self, base_url: str, config: BuildConfig) -> None:
        self.base_url = base_url
        self.config = config
        self.surface = ApiSurface()
        self._seen_endpoints: set[str] = set()
        self._seen_forms: set[str] = set()
        self._seen_observed: set[str] = set()
        self._scanned_js: set[str] = set()

    # -- per-page collection ------------------------------------------------
    def collect_from_page(self, page_id: str, page_url: str, structure: PageStructure) -> None:
        for form in structure.forms:
            key = f"{form.method} {normalize_url(form.action_url)} {','.join(f.name for f in form.fields)}"
            if key in self._seen_forms:
                continue
            self._seen_forms.add(key)
            self.surface.forms.append(
                {
                    "form_id": form.form_id,
                    "page_id": page_id,
                    "method": form.method,
                    "action_url": form.action_url,
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.input_type,
                            "label": f.label,
                            "required": f.required,
                            "options": f.options,
                        }
                        for f in form.fields
                    ],
                    "submit_labels": form.submit_labels,
                    "source": "html_form",
                }
            )

        for link in structure.links:
            if _API_PATH_RE.search(link.url):
                self._add_endpoint(link.url, "GET", "api_link", page_id, note=link.text[:80])

        for feed in structure.feeds:
            if not any(f["url"] == feed["url"] for f in self.surface.feeds):
                self.surface.feeds.append({**feed, "page_id": page_id, "source": "link_rel"})

        for script_text in structure.inline_scripts:
            self._scan_js(script_text, page_id, origin="inline_script")

    def collect_external_js(self, script_urls: list[str]) -> None:
        budget = self.config.max_js_files - len(self._scanned_js)
        for url in script_urls:
            if budget <= 0:
                break
            url = normalize_url(url)
            if url in self._scanned_js or not same_site(url, self.base_url):
                continue
            self._scanned_js.add(url)
            budget -= 1
            result = fetch(url, timeout=self.config.timeout, max_bytes=self.config.max_js_bytes, retries=0)
            if result.ok:
                self._scan_js(result.text(self.config.max_js_bytes), page_id="", origin=url)

    def _scan_js(self, text: str, page_id: str, origin: str) -> None:
        for match in _JS_CALL_RE.finditer(text):
            self._maybe_add_js_url(match.group(1), page_id, origin)
        for match in _JS_URL_RE.finditer(text):
            self._maybe_add_js_url(match.group(1), page_id, origin)

    def _maybe_add_js_url(self, raw: str, page_id: str, origin: str) -> None:
        raw = raw.strip()
        if not raw or raw.startswith(("data:", "blob:", "#", "javascript:")):
            return
        if "${" in raw or "\\" in raw:  # template literal placeholder / escapes
            return
        url = urljoin(self.base_url, raw)
        if not urlsplit(url).scheme.startswith("http"):
            return
        if not (_API_PATH_RE.search(url) or raw.startswith("/")):
            return
        self._add_endpoint(url, "GET", "javascript", page_id, note=f"found in {origin}"[:120])

    def _add_endpoint(self, url: str, method: str, source: str, page_id: str, note: str = "") -> None:
        url = normalize_url(url)
        key = f"{method} {url}"
        if key in self._seen_endpoints:
            return
        self._seen_endpoints.add(key)
        self.surface.endpoints.append(
            {
                "method": method,
                "url": url,
                "path": urlsplit(url).path or "/",
                "same_origin": same_origin(url, self.base_url),
                "source": source,
                "page_id": page_id,
                "note": note,
            }
        )

    # -- network log from renderer -------------------------------------------
    def collect_network_log(self, entries: list[dict]) -> None:
        for entry in entries:
            url = normalize_url(entry.get("url", ""))
            method = entry.get("method", "GET").upper()
            if not url:
                continue
            ctype = (entry.get("response_content_type") or "").lower()
            api_like = (
                entry.get("resource_type") in ("xhr", "fetch")
                or "json" in ctype
                or _API_PATH_RE.search(url) is not None
            )
            if not api_like:
                continue
            key = f"{method} {url.split('?')[0]}"
            if key in self._seen_observed:
                continue
            self._seen_observed.add(key)
            self.surface.observed_network.append(
                {
                    "method": method,
                    "url": url,
                    "path": urlsplit(url).path or "/",
                    "status": entry.get("status"),
                    "resource_type": entry.get("resource_type"),
                    "response_content_type": ctype,
                    "same_origin": same_origin(url, self.base_url),
                    "page_id": entry.get("page_id", ""),
                    "source": "network_observation",
                }
            )

    # -- site-level probes ----------------------------------------------------
    def probe_well_known(self) -> None:
        if not self.config.probe_well_known:
            return
        for path in _OPENAPI_PROBES:
            url = urljoin(self.base_url, path)
            result = fetch(url, timeout=min(self.config.timeout, 10.0), max_bytes=2_000_000, retries=0)
            if result.ok and ("json" in result.content_type or path.endswith(".json")):
                try:
                    doc = json.loads(result.text())
                except ValueError:
                    continue
                if isinstance(doc, dict) and ("openapi" in doc or "swagger" in doc):
                    info = doc.get("info", {}) if isinstance(doc.get("info"), dict) else {}
                    self.surface.openapi.append(
                        {
                            "url": result.final_url,
                            "version": doc.get("openapi") or doc.get("swagger"),
                            "title": info.get("title", ""),
                            "paths": sorted(list(doc.get("paths", {}).keys()))[:200]
                            if isinstance(doc.get("paths"), dict)
                            else [],
                            "source": "openapi_probe",
                        }
                    )
                    break  # one spec is enough

        for path in _WELL_KNOWN_PROBES:
            url = urljoin(self.base_url, path)
            result = fetch(url, timeout=min(self.config.timeout, 10.0), max_bytes=500_000, retries=0)
            if result.ok and result.body:
                entry: dict = {"url": result.final_url, "path": path, "content_type": result.content_type}
                if "json" in result.content_type:
                    try:
                        payload = json.loads(result.text())
                        if isinstance(payload, dict):
                            entry["keys"] = sorted(payload.keys())[:30]
                    except ValueError:
                        continue
                self.surface.well_known.append(entry)

    def probe_sitemap(self) -> list[str]:
        """Fetch sitemap.xml (expanding one level of sitemap-index files);
        return contained page URLs (also used as crawl seeds)."""
        if not self.config.probe_well_known:
            return []
        url = urljoin(self.base_url, "/sitemap.xml")
        locs = self._fetch_sitemap_locs(url)
        if not locs:
            return []
        # Expand sitemap-index children (WordPress/Yoast layout): child .xml
        # locs are themselves sitemaps, not pages.
        page_urls: list[str] = []
        child_budget = 5
        for loc in locs:
            if loc.lower().rstrip("/").endswith((".xml", ".xml.gz")) and child_budget > 0:
                child_budget -= 1
                page_urls.extend(u for u in self._fetch_sitemap_locs(loc)
                                 if not u.lower().rstrip("/").endswith((".xml", ".xml.gz")))
            else:
                page_urls.append(loc)
        self.surface.sitemaps.append(
            {
                "url": url,
                "url_count": len(page_urls),
                "sample": page_urls[:20],
                "source": "sitemap_probe",
            }
        )
        return page_urls

    def _fetch_sitemap_locs(self, url: str) -> list[str]:
        result = fetch(url, timeout=min(self.config.timeout, 10.0), max_bytes=4_000_000, retries=0)
        if not result.ok or not result.body:
            return []
        text = result.text()
        locs = re.findall(
            r"<loc>\s*(?:<!\[CDATA\[\s*(.*?)\s*\]\]>|([^<\s]+))\s*</loc>", text, re.DOTALL
        )
        # findall returns tuples (cdata, plain); XML entities must be decoded.
        return [unescape((a or b).strip()) for a, b in locs if (a or b).strip()]
