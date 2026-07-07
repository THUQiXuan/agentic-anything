"""Regression tests for the v0.2 adversarial-review findings."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_anything.chat import LocalPeer, ResourceAgent
from agentic_anything.ingest import (
    IngestError,
    Unit,
    _split_large_units,
    build_pack_from_source,
    detect_source_kind,
    ingest_directory,
    ingest_file,
)

RESOURCES = Path(__file__).parent / "fixtures" / "resources"


# ----------------------------------------------------------- markdown -------

def test_md_fence_with_inner_backticks(tmp_path):
    md = tmp_path / "f.md"
    md.write_text(
        "# Real\n\n"
        "````markdown\n"
        "```\n"
        "# inside example\n"
        "```\n"
        "````\n\n"
        "## Second real\n\nbody\n",
        encoding="utf-8",
    )
    _, units = ingest_file(md)
    titles = [u.title for u in units]
    assert "inside example" not in titles          # fence content is not a heading
    assert "Second real" in titles                 # real heading after fence survives
    real = next(u for u in units if u.title == "Real")
    pre = [c for c in real.content if c["kind"] == "pre"]
    assert pre and "# inside example" in pre[0]["text"]


def test_md_tilde_fence(tmp_path):
    md = tmp_path / "t.md"
    md.write_text("~~~\n# not a heading\n~~~\n\n# Yes heading\n\nx\n", encoding="utf-8")
    _, units = ingest_file(md)
    titles = [u.title for u in units]
    assert "not a heading" not in titles
    assert "Yes heading" in titles


def test_md_fence_blank_lines_stay_one_block(tmp_path):
    md = tmp_path / "b.md"
    md.write_text(
        "# T\n\n```python\n# not a heading\nx = 1\n\n# also not a heading\ny = 2\n```\n",
        encoding="utf-8",
    )
    _, units = ingest_file(md)
    unit = next(u for u in units if u.title == "T")
    pre = [c for c in unit.content if c["kind"] == "pre"]
    assert len(pre) == 1
    assert "x = 1" in pre[0]["text"] and "y = 2" in pre[0]["text"]  # not split
    assert pre[0].get("lang") == "python"                            # info string kept
    assert "```" not in pre[0]["text"]


def test_md_heading_trailing_hash_kept(tmp_path):
    md = tmp_path / "h.md"
    md.write_text("# Learning C#\n\nbody\n", encoding="utf-8")
    _, units = ingest_file(md)
    assert units[0].title == "Learning C#"


def test_md_inline_backticks_preserved(tmp_path):
    md = tmp_path / "i.md"
    md.write_text("# T\n\n`code` at start and end `tick`\n", encoding="utf-8")
    _, units = ingest_file(md)
    para = [c for c in units[0].content if c["kind"] == "p"][0]
    assert para["text"] == "`code` at start and end `tick`"


# ----------------------------------------------------------- subtitles ------

def test_vtt_hourless_timestamps(tmp_path):
    vtt = tmp_path / "cap.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:01.000 --> 00:04.000\nHourless cue text here.\n\n"
        "00:05.000 --> 00:08.000\nSecond cue.\n",
        encoding="utf-8",
    )
    _, units = ingest_file(vtt)
    assert "Hourless cue text here." in units[0].text()
    assert units[0].meta["start_seconds"] == pytest.approx(1.0)


def test_vtt_cue_settings_not_in_text(tmp_path):
    vtt = tmp_path / "set.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:04.000 position:10%,line-left align:start size:35%\n"
        "Where did he go?\n",
        encoding="utf-8",
    )
    _, units = ingest_file(vtt)
    text = units[0].text()
    assert "Where did he go?" in text
    assert "position" not in text and "align:start" not in text


def test_srt_overlapping_cues_window_end(tmp_path):
    srt = tmp_path / "o.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:05:00,000\nLong cue.\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nShort inner cue.\n",
        encoding="utf-8",
    )
    _, units = ingest_file(srt)
    assert units[0].meta["end_seconds"] == pytest.approx(300.0)  # max end, not last


# ----------------------------------------------------------- encodings ------

def test_cp1252_not_mojibake(tmp_path):
    f = tmp_path / "cafe.txt"
    f.write_bytes("The cafés serve crème brûlée daily.".encode("cp1252"))
    _, units = ingest_file(f)
    assert "crème brûlée" in units[0].text()


def test_utf16_bom(tmp_path):
    f = tmp_path / "u16.txt"
    f.write_bytes("hello utf sixteen".encode("utf-16"))
    _, units = ingest_file(f)
    assert "hello utf sixteen" in units[0].text()


def test_gbk_still_works(tmp_path):
    f = tmp_path / "cn.txt"
    f.write_bytes("这是一个中文段落，用于验证编码回退。".encode("gb18030"))
    _, units = ingest_file(f)
    assert "中文段落" in units[0].text()


# ----------------------------------------------------------- directories ----

def test_dot_ancestor_does_not_block_ingest(tmp_path):
    root = tmp_path / ".hidden" / "library"
    root.mkdir(parents=True)
    (root / "notes.md").write_text("# N\n\ncontent\n", encoding="utf-8")
    _, units, _ = ingest_directory(root)
    assert units  # ancestor dot-dir must not exclude the corpus itself


def test_dir_prefix_no_collisions(tmp_path):
    root = tmp_path / "lib"
    (root / "a").mkdir(parents=True)
    (root / "a" / "b.md").write_text("# Same\n\nx\n", encoding="utf-8")
    (root / "a-b.md").write_text("# Same\n\ny\n", encoding="utf-8")
    (root / "notes.md").write_text("# Same\n\nz\n", encoding="utf-8")
    (root / "notes.txt").write_text("Same z2\n", encoding="utf-8")
    _, units, _ = ingest_directory(root)
    ids = [u.unit_id for u in units]
    assert len(ids) == len(set(ids)), f"duplicate unit ids: {ids}"


def test_dir_skips_are_reported(tmp_path):
    root = tmp_path / "mix"
    root.mkdir()
    (root / "good.md").write_text("# G\n\nok\n", encoding="utf-8")
    (root / "empty.srt").write_text("no cues at all\n", encoding="utf-8")
    result = build_pack_from_source(str(root), tmp_path / "pack")
    assert result.page_count >= 1
    assert any("empty.srt" in w for w in result.warnings)


def test_typo_filename_not_treated_as_url(tmp_path):
    with pytest.raises(IngestError, match="file not found"):
        detect_source_kind("noteZ.txt")


# ----------------------------------------------------------- splitting ------

def test_split_single_oversize_part_keeps_identity():
    unit = Unit(unit_id="ch1", title="Chapter 1", kind="chapter",
                content=[{"kind": "p", "text": "a" * 100},
                         {"kind": "p", "text": "b" * 25000}])
    out = _split_large_units([unit])
    assert len(out) == 1
    assert out[0].unit_id == "ch1"           # no phantom '(part 1)'
    assert out[0].title == "Chapter 1"


# ----------------------------------------------------------- chat/A2A -------

def test_peer_prompt_suppressed_when_allow_peers_false(tmp_path, scripted_llm):
    build_pack_from_source(str(RESOURCES / "handbook.md"), tmp_path / "h", site_id="h")
    build_pack_from_source(str(RESOURCES / "lecture.srt"), tmp_path / "l", site_id="l")
    config = scripted_llm.config()
    agent_l = ResourceAgent(tmp_path / "l", config)
    agent_h = ResourceAgent(tmp_path / "h", config,
                            peers={"l": LocalPeer("l", agent_l)})
    # give l a peer too, mimicking serve --enable-a2a topology
    agent_l.peers = {"h": LocalPeer("h", agent_h)}

    scripted_llm.push(
        "@ask l What is E42?",
        "E42 means the cache is stale.",   # l's own answer
        "Final: cache is stale.",
    )
    agent_h.ask("What is E42?")
    # The peer's LLM call (2nd request) must NOT contain the @ask instructions,
    # since it was invoked with allow_peers=False.
    peer_system = scripted_llm.seen[1]["messages"][0]["content"]
    assert "@ask" not in peer_system
    assert "Peer agents" not in peer_system


def test_multiline_answer_starting_with_ask_not_intercepted(tmp_path, scripted_llm):
    build_pack_from_source(str(RESOURCES / "handbook.md"), tmp_path / "h", site_id="h")
    config = scripted_llm.config()
    dummy_peer_target = ResourceAgent(tmp_path / "h", config)
    agent = ResourceAgent(tmp_path / "h", config,
                          peers={"lecture": LocalPeer("lecture", dummy_peer_target)})
    answer = "@ask lecture is not needed here.\n\nThe Team tier costs $79."
    scripted_llm.push(answer)
    reply = agent.ask("price?")
    assert reply.answer == answer            # returned verbatim, no peer call
    assert reply.peer_calls == []


def test_hop_exhaustion_no_scaffolding_leak(tmp_path, scripted_llm):
    build_pack_from_source(str(RESOURCES / "handbook.md"), tmp_path / "h", site_id="h")
    build_pack_from_source(str(RESOURCES / "lecture.srt"), tmp_path / "l", site_id="l")
    config = scripted_llm.config()
    agent_l = ResourceAgent(tmp_path / "l", config)
    agent = ResourceAgent(tmp_path / "h", config,
                          peers={"l": LocalPeer("l", agent_l)})
    scripted_llm.push(
        "@ask l q1", "peer answer 1",
        "@ask l q2", "peer answer 2",
        "@ask l q3",
    )
    reply = agent.ask("loop")
    assert len(reply.peer_calls) == 2
    assert "== PEER ANSWER" not in reply.answer   # no internal scaffolding
    assert "peer answer 2" in reply.answer        # but the useful content is there


def test_openai_endpoint_trailing_assistant(tmp_path, scripted_llm):
    import json as jsonlib
    import urllib.request

    from agentic_anything.server import AgentServer

    build_pack_from_source(str(RESOURCES / "handbook.md"), tmp_path / "h", site_id="h")
    server = AgentServer([tmp_path / "h"], scripted_llm.config(), port=0)
    server.start_background()
    try:
        scripted_llm.push("answer text")
        body = jsonlib.dumps({
            "model": "h",
            "messages": [
                {"role": "user", "content": "the real question"},
                {"role": "assistant", "content": "prefill fragment"},
            ],
        }).encode()
        request = urllib.request.Request(
            f"{server.base_url}/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as resp:
            payload = jsonlib.loads(resp.read())
        assert payload["choices"][0]["message"]["content"] == "answer text"
        # question was the LAST USER turn, not the trailing assistant turn
        llm_user_msg = scripted_llm.seen[-1]["messages"][-1]["content"]
        assert "the real question" in llm_user_msg
    finally:
        server.shutdown()
