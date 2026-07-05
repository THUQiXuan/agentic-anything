from agentic_anything.util import (
    normalize_url,
    page_id_from_url,
    same_origin,
    site_slug_from_url,
    slugify,
    truncate_text,
)


def test_slugify():
    assert slugify("Quotes to Scrape!") == "quotes-to-scrape"
    assert slugify("  ") == "site"
    assert slugify("中文站点") == "site"  # non-ascii collapses to fallback


def test_site_slug_from_url():
    assert site_slug_from_url("https://www.example.com/path") == "example-com"
    assert site_slug_from_url("http://sub.demo.io:8080/") == "sub-demo-io"


def test_page_id_from_url():
    assert page_id_from_url("https://x.com/") == "index"
    assert page_id_from_url("https://x.com/docs/api") == "docs__api"
    assert page_id_from_url("https://x.com/docs/api/") == "docs__api"
    with_query = page_id_from_url("https://x.com/a?page=2")
    assert with_query.startswith("a__q_") and len(with_query) > 6
    # stable
    assert with_query == page_id_from_url("https://x.com/a?page=2")


def test_normalize_url():
    assert normalize_url("HTTPS://X.com/a/") == "https://x.com/a"
    assert normalize_url("https://x.com/a#frag") == "https://x.com/a"
    assert normalize_url("https://x.com//a//b") == "https://x.com/a/b"
    assert normalize_url("https://x.com/") == "https://x.com/"


def test_same_origin():
    assert same_origin("https://x.com/a", "https://x.com/b")
    assert not same_origin("https://x.com", "https://y.com")
    assert not same_origin("http://x.com", "https://x.com")


def test_truncate_text():
    assert truncate_text("abc", 10) == "abc"
    out = truncate_text("a" * 50, 10)
    assert len(out) <= 10 and out.endswith("…")
