"""Deep capture: linked documents, repositories, and videos found while
crawling become ingested pack pages (within budgets) or frontier entries —
never silent drops."""

from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import agentic_anything.ingest as ingest_mod
from agentic_anything.config import BuildConfig
from agentic_anything.crawler import attachment_kind
from agentic_anything.ingest import AssetIngest, Unit
from agentic_anything.packer import build_pack
from agentic_anything.query import PackReader, search_pack

FIXTURES = Path(__file__).parent / "fixtures" / "course_site"


@pytest.fixture(scope="module")
def course_server():
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

    handler = partial(Handler, directory=str(FIXTURES))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    thread.join(timeout=5)


def _site(pack_dir: Path) -> dict:
    return json.loads((pack_dir / "site.json").read_text(encoding="utf-8"))


def _skip_reason_by_suffix(site: dict, suffix: str) -> str | None:
    for entry in site["frontier"]:
        if entry["url"].split("?")[0].endswith(suffix) or suffix in entry["url"]:
            return entry["skip_reason"]
    return None


def test_attachment_kind_classifier():
    assert attachment_kind("https://a.edu/slides/lecture3.pdf") == "document"
    assert attachment_kind("https://a.edu/notes.md") == "document"
    assert attachment_kind("https://a.edu/data.csv") == "document"
    assert attachment_kind("https://a.edu/release.zip") == "archive"
    assert attachment_kind("https://github.com/example/starter-kit/tree/main") == "repo"
    assert attachment_kind("https://github.com/example/kit/blob/main/spec.pdf") == "document"
    assert attachment_kind("https://www.youtube.com/watch?v=x") == "video"
    assert attachment_kind("https://a.edu/about.html") is None
    assert attachment_kind("https://a.edu/logo.png") is None


def test_follow_disabled_records_frontier_instead_of_dropping(course_server, tmp_path):
    out = tmp_path / "pack"
    config = BuildConfig(max_pages=4, timeout=10.0)
    result = build_pack(f"{course_server}/index.html", out, config=config, site_id="course")
    assert result.attachment_count == 0
    site = _site(out)
    assert site["attachments"] == []
    assert _skip_reason_by_suffix(site, "/notes.md") == "attachment_not_followed"
    assert _skip_reason_by_suffix(site, "/data/measurements.csv") == "attachment_not_followed"
    assert _skip_reason_by_suffix(site, "starter-kit/tree/main") == "attachment_not_followed"
    assert _skip_reason_by_suffix(site, "youtube.com/watch") == "video_link_recorded"


def test_docs_followed_into_pack(course_server, tmp_path):
    out = tmp_path / "pack"
    config = BuildConfig(max_pages=4, timeout=10.0, follow_docs=2)
    result = build_pack(f"{course_server}/index.html", out, config=config, site_id="course")
    assert result.attachment_count == 2

    site = _site(out)
    followed = {a["url"].rsplit("/", 1)[-1]: a for a in site["attachments"]}
    assert set(followed) == {"notes.md", "measurements.csv"}
    for att in site["attachments"]:
        assert att["kind"] == "document"
        assert att["content_sha256"]
        assert att["content_bytes"] > 0
        assert att["from_page_id"]
        assert att["unit_count"] >= 1

    # the third document hits the budget; nothing is silently dropped
    assert _skip_reason_by_suffix(site, "/extra.csv") == "attachment_budget_exhausted"
    # off-site host is refused before any fetch
    assert _skip_reason_by_suffix(site, "widget-theory.pdf") == "attachment_host_not_allowed"
    # video links are recorded, never downloaded
    assert _skip_reason_by_suffix(site, "youtube.com/watch") == "video_link_recorded"

    # attachment pages are first-class pack pages
    att_pages = [p for p in site["pages"] if p.get("discovered_via") == "attachment"]
    assert att_pages
    reader = PackReader(out)
    for entry in att_pages:
        manifest = reader.page(entry["page_id"])
        prov = manifest["provenance"]
        assert prov["discovered_via"] == "attachment"
        assert prov["attachment_kind"] == "document"
        assert prov["from_page_id"] == "index"
        assert prov["attachment_sha256"]
        assert (out / "pages" / f"{entry['page_id']}.md").exists()

    # and they are retrievable like any crawled page
    hits = search_pack(out, "widget temperature dataset run", top=5)
    att_ids = {p["page_id"] for p in att_pages}
    assert any(hit["page_id"] in att_ids for hit in hits)

    # capability flag is advertised
    discovery = json.loads((out / "agent-pack.json").read_text(encoding="utf-8"))
    assert "linked_attachments" in discovery["capabilities"]


def test_repo_follow_merges_prefixed_units(course_server, tmp_path, monkeypatch):
    def fake_units_for_url_asset(url, *, max_bytes=None, timeout=60.0):
        assert "starter-kit" in url
        units = [
            Unit(unit_id="tree", title="repository tree", kind="code",
                 content=[{"kind": "p", "text": "src/ README.md"}],
                 source_path=url, locator="tree"),
            Unit(unit_id="file__readme-md", title="README.md", kind="code",
                 content=[{"kind": "p", "text": "Starter kit for the course."}],
                 source_path=url, locator="README.md"),
        ]
        return AssetIngest(
            kind="repo", resource_type="code", title="example/starter-kit",
            units=units, source_label=url,
            fetched_url="https://codeload.github.com/example/starter-kit/zip/refs/heads/main",
            content_sha256="f" * 64, content_bytes=1234,
        )

    monkeypatch.setattr(ingest_mod, "units_for_url_asset", fake_units_for_url_asset)
    out = tmp_path / "pack"
    config = BuildConfig(max_pages=4, timeout=10.0, follow_repos=1,
                         respect_robots=False)
    result = build_pack(f"{course_server}/index.html", out, config=config, site_id="course")
    assert result.attachment_count == 1

    site = _site(out)
    att = site["attachments"][0]
    assert att["kind"] == "repo"
    assert att["resource_type"] == "code"
    assert att["title"] == "example/starter-kit"
    assert att["unit_count"] == 2

    repo_pages = [p for p in site["pages"] if p.get("attachment_kind") == "repo"]
    assert len(repo_pages) == 2
    for entry in repo_pages:
        assert entry["page_id"].startswith("example-starter-kit__")
        manifest = PackReader(out).page(entry["page_id"])
        assert manifest["provenance"]["attachment_kind"] == "repo"


def test_follow_host_allowlist(course_server, tmp_path, monkeypatch):
    seen: list[str] = []

    def fake_units_for_url_asset(url, *, max_bytes=None, timeout=60.0):
        seen.append(url)
        raise ingest_mod.IngestError("offline test refuses to fetch")

    monkeypatch.setattr(ingest_mod, "units_for_url_asset", fake_units_for_url_asset)
    out = tmp_path / "pack"
    config = BuildConfig(max_pages=4, timeout=10.0, follow_docs=3,
                         follow_hosts=["offsite.invalid"], respect_robots=False)
    build_pack(f"{course_server}/index.html", out, config=config, site_id="course")
    site = _site(out)
    # the allowlisted off-site host was attempted (and failed loudly)
    assert any("offsite.invalid" in u for u in seen)
    assert _skip_reason_by_suffix(site, "widget-theory.pdf").startswith(
        "attachment_fetch_failed")
