from pathlib import Path

from agentic_anything.parser import parse_html

FIXTURES = Path(__file__).parent / "fixtures" / "demo_site"
BASE = "http://demo.local"


def _parse(name: str, base_path: str = "/"):
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return parse_html(html, f"{BASE}{base_path}")


def test_index_basics():
    page = _parse("index.html")
    assert page.title == "Acme Cloud — Home"
    assert page.lang == "en"
    assert "agent-native capture" in page.meta_description
    assert page.canonical_url == "http://demo.local/"
    assert [h.text for h in page.headings if h.level == 1] == ["Welcome to Acme Cloud"]
    texts = [b.text for b in page.blocks]
    assert "Acme Cloud provides scalable widget hosting for modern teams." in texts
    assert "Deploy widgets in seconds" in texts


def test_index_links_and_nav():
    page = _parse("index.html")
    nav_links = [l for l in page.links if l.is_nav]
    assert {l.url for l in nav_links} == {
        f"{BASE}/index.html", f"{BASE}/pricing.html", f"{BASE}/contact.html", f"{BASE}/docs/api.html",
    }
    partner = [l for l in page.links if "partner" in l.url]
    assert partner and not partner[0].is_nav
    # image link picks up alt text as link text
    img_link = [l for l in page.links if l.url == f"{BASE}/pricing.html" and not l.is_nav][0]
    assert "Compare Acme Cloud plans" in img_link.text


def test_index_scripts_feeds_jsonld():
    page = _parse("index.html")
    assert f"{BASE}/app.js" in page.script_srcs
    assert any("fetch('/api/quotes')" in s for s in page.inline_scripts)
    assert page.feeds and page.feeds[0]["url"] == f"{BASE}/feed.xml"
    assert page.json_ld and page.json_ld[0]["@type"] == "Organization"
    assert page.images and page.images[0].alt == "Compare Acme Cloud plans"


def test_content_stream_order():
    page = _parse("index.html")
    kinds = [c["kind"] for c in page.content]
    # first heading precedes the first paragraph in document order
    assert kinds.index("heading") < kinds.index("p")
    heading_entries = [c for c in page.content if c["kind"] == "heading"]
    assert heading_entries[0]["level"] == 1


def test_contact_form():
    page = _parse("contact.html")
    assert len(page.forms) == 1
    form = page.forms[0]
    assert form.form_id == "contact-form"
    assert form.method == "POST"
    assert form.action_url == f"{BASE}/submit"
    names = {f.name: f for f in form.fields}
    assert set(names) == {"full_name", "work_email", "topic", "message", "csrf"}
    assert names["full_name"].required
    assert names["full_name"].label == "Full name"
    assert names["work_email"].input_type == "email"
    assert names["work_email"].placeholder == "you@company.com"
    assert names["topic"].input_type == "select"
    assert names["topic"].options == ["Sales", "Support", "Partnership"]
    assert names["message"].input_type == "textarea"
    assert form.submit_labels == ["Send message"]


def test_pricing_table_blocks():
    page = _parse("pricing.html")
    texts = [b.text for b in page.blocks]
    assert "$79/month" in texts
    assert "Team plan" in texts


def test_malformed_html_does_not_crash():
    page = parse_html("<html><body><p>ok<div><a href='/x'>link</a>", "http://demo.local/")
    assert any(b.text == "ok" for b in page.blocks)
    assert any(l.url == "http://demo.local/x" for l in page.links)


def test_summary():
    page = _parse("index.html")
    summary = page.text_summary()
    assert "Welcome to Acme Cloud" in summary


def test_loose_text_in_divs_and_spans_captured():
    # Real-world pattern (quotes.toscrape.com): content lives in spans/divs
    # without semantic block tags.
    html = """
    <html><body>
      <div class="quote">
        <span class="text">“The world as we have created it is a process of our thinking.”</span>
        <span>by <small class="author">Albert Einstein</small></span>
      </div>
      <div class="quote">
        <span class="text">“It is our choices that show what we truly are.”</span>
      </div>
    </body></html>
    """
    page = parse_html(html, "http://demo.local/")
    texts = " ".join(b.text for b in page.blocks)
    assert "process of our thinking" in texts
    assert "Albert Einstein" in texts
    assert "our choices" in texts


def test_loose_text_not_duplicating_paragraphs():
    html = "<div><p>real paragraph</p></div>"
    page = parse_html(html, "http://demo.local/")
    assert [b.text for b in page.blocks] == ["real paragraph"]
