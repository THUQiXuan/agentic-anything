"""Rendered-mode capture (requires the [render] extra + Chromium).

These tests are skipped automatically when Playwright is not installed,
since rendering is an optional feature.
"""

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

from agentic_anything.config import BuildConfig
from agentic_anything.packer import build_pack
from agentic_anything.util import read_json

DYNAMIC_DIR = Path(__file__).parent / "fixtures" / "dynamic_site"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def dynamic_server():
    handler = partial(_QuietHandler, directory=str(DYNAMIC_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def rendered_pack(dynamic_server, tmp_path_factory):
    out = tmp_path_factory.mktemp("rendered") / "dyn"
    config = BuildConfig(
        max_pages=3, timeout=30.0, render=True, screenshots=True,
        probe_well_known=False, respect_robots=False,
    )
    result = build_pack(f"{dynamic_server}/index.html", out, config=config, site_id="dyn")
    assert result.page_count >= 1
    return out


def test_js_content_captured(rendered_pack):
    manifest = read_json(rendered_pack / "pages" / "index.json")
    texts = [c["text"] for c in manifest["content"]]
    assert any("Loaded 3 widgets dynamically" in t for t in texts)
    assert any("turbo widget" in t for t in texts)
    assert manifest["provenance"]["capture_mode"] == "rendered"


def test_js_added_link_followed(rendered_pack):
    site = read_json(rendered_pack / "site.json")
    ids = {p["page_id"] for p in site["pages"]}
    assert "detail" in ids  # link only exists after JS runs


def test_network_sniffing(rendered_pack):
    apis = read_json(rendered_pack / "api" / "apis.json")
    observed = apis["observed_network"]
    assert any(o["url"].endswith("/api/widgets.json") for o in observed)
    assert any(o.get("status") == 200 for o in observed)


def test_render_mode_rejects_http_error_pages(dynamic_server, tmp_path):
    # A 404 must not be captured as content with a fabricated status=200.
    config = BuildConfig(max_pages=2, timeout=30.0, render=True,
                         probe_well_known=False, respect_robots=False)
    result = build_pack(f"{dynamic_server}/nope.html", tmp_path / "err", config=config,
                        site_id="err")
    assert result.page_count == 0
    site = read_json(tmp_path / "err" / "site.json")
    assert any(f["skip_reason"] == "fetch_failed_http_404" for f in site["frontier"])


def test_screenshots_written(rendered_pack):
    snap = rendered_pack / "snapshots" / "index.png"
    assert snap.exists()
    assert snap.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    manifest = read_json(rendered_pack / "pages" / "index.json")
    assert manifest["snapshot_path"] == "snapshots/index.png"
    discovery = read_json(rendered_pack / "agent-pack.json")
    assert "visual_snapshots" in discovery["capabilities"]
