import pytest

from agentic_anything.query import PackNotFound, PackReader, _evidence, search_pack


def test_pack_reader_info(built_pack):
    reader = PackReader(built_pack)
    info = reader.info()
    assert info["site_id"] == "demo"
    assert info["page_count"] >= 5
    assert info["capture_mode"] == "static"
    assert info["api_surface"]["forms"] >= 1
    assert info["has_skill"] is False


def test_pack_reader_page(built_pack):
    reader = PackReader(built_pack)
    page = reader.page("pricing")
    assert page["title"] == "Acme Cloud — Pricing"
    md = reader.page_markdown("pricing")
    assert md.startswith("# Acme Cloud — Pricing")
    with pytest.raises(PackNotFound):
        reader.page("nope")


def test_pack_reader_rejects_non_pack(tmp_path):
    with pytest.raises(PackNotFound):
        PackReader(tmp_path)


def test_search_finds_pricing(built_pack):
    results = search_pack(built_pack, "team plan price", top=3)
    assert results
    assert results[0]["page_id"] == "pricing"
    evidence_text = " ".join(e["text"] for e in results[0]["evidence"])
    assert "Team plan" in evidence_text or "$79/month" in evidence_text


def test_search_finds_form_page(built_pack):
    results = search_pack(built_pack, "contact sales email message")
    assert any(r["page_id"] == "contact" for r in results)


def test_search_empty_query(built_pack):
    assert search_pack(built_pack, "!!!") == []


def test_evidence_focuses_long_blocks_and_ranks_query_coverage():
    manifest = {
        "title": "Long real-world resource",
        "content": [
            {"kind": "p", "text": "attention appears alone"},
            {
                "kind": "p",
                "text": "unrelated preface " * 80
                + "Scaled dot-product attention divides logits before softmax."
                + " trailing appendix" * 80,
            },
        ],
    }
    evidence = _evidence(manifest, "scaled dot product attention")
    assert evidence[0]["matched"] == ["attention", "dot", "product", "scaled"]
    assert "Scaled dot-product attention" in evidence[0]["text"]
    assert len(evidence[0]["text"]) <= 302
