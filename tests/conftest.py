"""Shared fixtures: a local HTTP server serving the demo site, and a
session-scoped pack built against it."""

from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from agentic_anything.config import BuildConfig
from agentic_anything.packer import build_pack

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "demo_site"


class _FixtureHandler(SimpleHTTPRequestHandler):
    """Serves the fixture dir; rewrites sitemap host to the live origin."""

    def log_message(self, *args) -> None:  # keep test output clean
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/sitemap.xml":
            origin = f"http://{self.headers.get('Host', 'localhost')}"
            body = (
                (FIXTURE_DIR / "sitemap.xml")
                .read_text(encoding="utf-8")
                .replace("http://demo.local", origin)
                .encode("utf-8")
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/quotes":
            body = (FIXTURE_DIR / "api" / "quotes").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


@pytest.fixture(scope="session")
def demo_server():
    handler = partial(_FixtureHandler, directory=str(FIXTURE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def built_pack(demo_server, tmp_path_factory):
    """One static-mode pack shared by read-only tests."""
    out = tmp_path_factory.mktemp("packs") / "demo"
    config = BuildConfig(max_pages=10, timeout=10.0)
    result = build_pack(f"{demo_server}/index.html", out, config=config, site_id="demo")
    assert result.page_count > 0
    return out
