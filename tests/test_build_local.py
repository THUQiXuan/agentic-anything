"""End-to-end build against the local fixture server (static mode)."""

import json
from pathlib import Path

from agentic_anything.config import BuildConfig
from agentic_anything.packer import build_pack
from agentic_anything.util import read_json


def test_pack_layout(built_pack: Path):
    assert (built_pack / "agent-pack.json").exists()
    assert (built_pack / "site.json").exists()
    assert (built_pack / "api" / "apis.json").exists()
    assert (built_pack / "pages" / "index.json").exists()
    assert (built_pack / "pages" / "index.md").exists()
    assert (built_pack / "html" / "index.html").exists()


def test_discovery_document(built_pack: Path):
    discovery = read_json(built_pack / "agent-pack.json")
    assert discovery["kind"] == "agentic-anything-pack"
    assert discovery["site_id"] == "demo"
    assert "page_manifests" in discovery["capabilities"]
    assert "api_surface" in discovery["capabilities"]
    assert discovery["contents"]["site_snapshot"] == "site.json"


def test_crawl_coverage_and_frontier(built_pack: Path):
    site = read_json(built_pack / "site.json")
    ids = {p["page_id"] for p in site["pages"]}
    # nav + content links
    assert {"index", "pricing", "contact", "docs__api"} <= ids
    # sitemap-discovered page not linked from anywhere
    assert "hidden" in ids
    # robots-disallowed page ends up in the frontier, never captured
    assert "private__secret" not in ids
    frontier = {f["candidate_page_id"]: f for f in site["frontier"]}
    assert frontier["private__secret"]["skip_reason"] == "robots_disallowed"
    # off-origin link recorded, not fetched
    off_origin = [f for f in site["frontier"] if "partner.example.org" in f["url"]]
    assert off_origin and off_origin[0]["skip_reason"] == "cross_site_filtered"


def test_page_manifest_contents(built_pack: Path):
    manifest = read_json(built_pack / "pages" / "contact.json")
    assert manifest["title"] == "Acme Cloud — Contact"
    form = manifest["forms"][0]
    assert form["method"] == "POST"
    assert any(f["name"] == "work_email" and f["required"] for f in form["fields"])
    prov = manifest["provenance"]
    assert prov["http_status"] == 200
    assert prov["capture_mode"] == "static"
    assert len(prov["content_sha256"]) == 64
    assert prov["html_path"] == "html/contact.html"


def test_page_markdown_view(built_pack: Path):
    md = (built_pack / "pages" / "pricing.md").read_text(encoding="utf-8")
    assert "# Acme Cloud — Pricing" in md
    assert "$79/month" in md
    assert "## Links" in md


def test_api_surface(built_pack: Path):
    apis = read_json(built_pack / "api" / "apis.json")
    # form from contact page
    assert any(
        f["method"] == "POST" and f["action_url"].endswith("/submit") for f in apis["forms"]
    )
    # endpoints from html links and js scanning
    urls = {e["url"] for e in apis["endpoints"]}
    assert any(u.endswith("/api/quotes") for u in urls)           # inline script + link
    assert any("/api/search" in u for u in urls)                  # external app.js fetch()
    assert any(u.endswith("/api/users") for u in urls)            # axios.get
    assert not any("${" in u for u in urls)                       # template literals skipped
    # openapi probe found the spec
    assert apis["openapi"] and apis["openapi"][0]["title"] == "Acme Cloud API"
    assert "/api/quotes" in apis["openapi"][0]["paths"]
    # sitemap recorded
    assert apis["sitemaps"] and apis["sitemaps"][0]["url_count"] == 3
    # feed from link rel=alternate
    assert apis["feeds"] and apis["feeds"][0]["url"].endswith("/feed.xml")


def test_page_budget(demo_server, tmp_path):
    config = BuildConfig(max_pages=2, timeout=10.0)
    result = build_pack(f"{demo_server}/index.html", tmp_path / "small", config=config)
    assert result.page_count == 2
    site = read_json(tmp_path / "small" / "site.json")
    assert any(f["skip_reason"] == "page_budget_exhausted" for f in site["frontier"])


def test_build_result_json(demo_server, tmp_path):
    config = BuildConfig(max_pages=3, timeout=10.0)
    result = build_pack(f"{demo_server}/index.html", tmp_path / "r", config=config)
    payload = result.as_json()
    assert json.dumps(payload)  # serializable
    assert payload["page_count"] == 3
    assert payload["site_id"]
