"""Regression tests for issues found in the adversarial review round."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agentic_anything.apis import ApiCollector
from agentic_anything.config import BuildConfig
from agentic_anything.crawler import crawl
from agentic_anything.fetcher import FetchResult, encode_url_for_fetch, fetch
from agentic_anything.parser import parse_html


# ---------------------------------------------------------------- parser ----

def test_no_double_unescape():
    # Source shows a literal "<div>" via entities; a second unescape pass
    # would turn "&lt;div&gt;" into "<div>" and corrupt technical docs.
    html = "<html><body><h1>Use &amp;lt;div&amp;gt; tags</h1><p>Codes &amp;amp; Entities</p></body></html>"
    page = parse_html(html, "http://x.com/")
    assert page.headings[0].text == "Use &lt;div&gt; tags"
    assert page.blocks[0].text == "Codes &amp; Entities"


def test_base_href_resolution():
    html = (
        '<html><head><base href="https://ex.com/"></head><body>'
        '<a href="about">About</a>'
        '<form action="submit" method="post"><input name="x"></form>'
        "</body></html>"
    )
    page = parse_html(html, "https://ex.com/blog/post1")
    assert page.links[0].url == "https://ex.com/about"
    assert page.forms[0].action_url == "https://ex.com/submit"


def test_textarea_default_content_not_page_text():
    html = "<html><body><form><textarea name='m'>Type your message here</textarea></form><p>real</p></body></html>"
    page = parse_html(html, "http://x.com/")
    texts = [b.text for b in page.blocks]
    assert "Type your message here" not in " ".join(texts)
    assert "real" in texts


def test_label_matches_field_id_not_name():
    html = (
        "<html><body><form>"
        '<input type="text" id="fld-email" name="email_address">'
        '<label for="fld-email">Your e-mail</label>'
        "</form></body></html>"
    )
    page = parse_html(html, "http://x.com/")
    assert page.forms[0].fields[0].label == "Your e-mail"


def test_meta_refresh_extracted():
    html = '<html><head><meta http-equiv="refresh" content="0;url=/home"></head><body></body></html>'
    page = parse_html(html, "http://x.com/landing")
    assert page.refresh_url == "http://x.com/home"


# --------------------------------------------------------------- fetcher ----

def test_encode_url_for_fetch_iri():
    assert encode_url_for_fetch("http://x.com/café") == "http://x.com/caf%C3%A9"
    assert "%E6%97%A5" in encode_url_for_fetch("http://x.com/日本語")
    # already-encoded URLs unchanged
    assert encode_url_for_fetch("http://x.com/a%20b?q=1&r=2") == "http://x.com/a%20b?q=1&r=2"


def test_fetch_result_decodes_declared_charset():
    body = "中文标题测试".encode("gbk")
    result = FetchResult(url="u", final_url="u", status=200, content_type="text/html",
                         body=body, charset="gbk")
    assert result.text() == "中文标题测试"


def test_fetch_result_sniffs_meta_charset():
    body = ('<html><head><meta charset="gbk"></head><body>中文</body></html>').encode("gbk")
    result = FetchResult(url="u", final_url="u", status=200, content_type="text/html",
                         body=body, charset="")
    assert "中文" in result.text()


# ---------------------------------------------------- crawl-level fixes -----

class _Handler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, str, bytes]] = {}

    def log_message(self, *args):
        pass

    def do_GET(self):
        entry = self.routes.get(self.path)
        if entry is None:
            self.send_response(404)
            body = b"<html><body><h1>Page not found</h1></body></html>"
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        status, ctype, body = entry
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def routed_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}", _Handler
    server.shutdown()
    thread.join(timeout=5)
    _Handler.routes = {}


def test_page_id_collision_minted_not_dropped(routed_server):
    base, handler = routed_server
    handler.routes = {
        "/": (200, "text/html",
              b'<html><body><a href="/a.html">A</a> <a href="/a.php">B</a></body></html>'),
        "/a.html": (200, "text/html", b"<html><body><p>content one</p></body></html>"),
        "/a.php": (200, "text/html", b"<html><body><p>totally different</p></body></html>"),
    }
    config = BuildConfig(max_pages=10, respect_robots=False, probe_well_known=False, timeout=5.0)
    outcome = crawl(f"{base}/", config)
    ids = {p.page_id for p in outcome.pages}
    assert "a" in ids
    assert "a~2" in ids  # second distinct page kept under a minted id


def test_identical_alias_recorded_in_frontier(routed_server):
    base, handler = routed_server
    same = b"<html><body><p>same content</p></body></html>"
    handler.routes = {
        "/": (200, "text/html",
              b'<html><body><a href="/a.html">A</a> <a href="/a.php">B</a></body></html>'),
        "/a.html": (200, "text/html", same),
        "/a.php": (200, "text/html", same),
    }
    config = BuildConfig(max_pages=10, respect_robots=False, probe_well_known=False, timeout=5.0)
    outcome = crawl(f"{base}/", config)
    dupes = [f for f in outcome.frontier if f.skip_reason == "duplicate_of_captured_page"]
    assert len(dupes) == 1  # the alias is recorded, not silently dropped


def test_unicode_href_fetchable(routed_server):
    base, handler = routed_server
    handler.routes = {
        "/": (200, "text/html",
              '<html><body><a href="/café">menu</a></body></html>'.encode("utf-8")),
        "/caf%C3%A9": (200, "text/html", b"<html><body><p>espresso list</p></body></html>"),
    }
    config = BuildConfig(max_pages=5, respect_robots=False, probe_well_known=False, timeout=5.0)
    outcome = crawl(f"{base}/", config)
    texts = [b.text for p in outcome.pages for b in p.structure.blocks]
    assert "espresso list" in texts


def test_meta_refresh_followed(routed_server):
    base, handler = routed_server
    handler.routes = {
        "/": (200, "text/html",
              b'<html><head><meta http-equiv="refresh" content="0;url=/home"></head><body></body></html>'),
        "/home": (200, "text/html", b"<html><body><h1>Real home</h1></body></html>"),
    }
    config = BuildConfig(max_pages=5, respect_robots=False, probe_well_known=False, timeout=5.0)
    outcome = crawl(f"{base}/", config)
    ids = {p.page_id for p in outcome.pages}
    assert "home" in ids
    home = next(p for p in outcome.pages if p.page_id == "home")
    assert home.discovered_via == "meta_refresh"


def test_gbk_site_not_mojibake(routed_server):
    base, handler = routed_server
    handler.routes = {
        "/": (200, "text/html; charset=gbk",
              "<html><body><h1>中文标题测试</h1></body></html>".encode("gbk")),
    }
    config = BuildConfig(max_pages=2, respect_robots=False, probe_well_known=False, timeout=5.0)
    outcome = crawl(f"{base}/", config)
    assert outcome.pages[0].structure.headings[0].text == "中文标题测试"


# ------------------------------------------------------------- sitemap ------

def test_sitemap_entities_cdata_and_index(routed_server):
    base, handler = routed_server
    index_xml = f"""<?xml version="1.0"?>
    <sitemapindex><sitemap><loc>{base}/post-sitemap.xml</loc></sitemap></sitemapindex>"""
    child_xml = f"""<?xml version="1.0"?>
    <urlset>
      <url><loc>{base}/search?q=shoes&amp;page=2</loc></url>
      <url><loc><![CDATA[{base}/cdata-page]]></loc></url>
    </urlset>"""
    handler.routes = {
        "/sitemap.xml": (200, "application/xml", index_xml.encode()),
        "/post-sitemap.xml": (200, "application/xml", child_xml.encode()),
    }
    collector = ApiCollector(f"{base}/", BuildConfig(timeout=5.0))
    urls = collector.probe_sitemap()
    assert f"{base}/search?q=shoes&page=2" in urls   # &amp; decoded
    assert f"{base}/cdata-page" in urls              # CDATA extracted
    assert not any(u.endswith(".xml") for u in urls) # index expanded, not passed through


# ------------------------------------------------------------ apis dedup ----

def test_observed_network_dedup_across_pages():
    collector = ApiCollector("http://x.com/", BuildConfig())
    entry = {"url": "http://x.com/api/data", "method": "GET",
             "resource_type": "fetch", "response_content_type": "application/json",
             "status": 200, "page_id": "index"}
    collector.collect_network_log([dict(entry)])
    collector.collect_network_log([dict(entry, page_id="about")])
    assert len(collector.surface.observed_network) == 1
