"""ResourceAgent chat behavior against the scripted fake LLM."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_anything.chat import LocalPeer, ResourceAgent
from agentic_anything.ingest import build_pack_from_source

RESOURCES = Path(__file__).parent / "fixtures" / "resources"


@pytest.fixture()
def handbook_pack(tmp_path):
    build_pack_from_source(str(RESOURCES / "handbook.md"), tmp_path / "handbook",
                           site_id="handbook")
    return tmp_path / "handbook"


@pytest.fixture()
def lecture_pack(tmp_path):
    build_pack_from_source(str(RESOURCES / "lecture.srt"), tmp_path / "lecture",
                           site_id="lecture")
    return tmp_path / "lecture"


def test_ask_grounds_in_pack_and_extracts_citations(handbook_pack, scripted_llm):
    agent = ResourceAgent(handbook_pack, scripted_llm.config())
    real_id = agent.reader.page_ids()[0]
    pricing_id = next(p for p in agent.reader.page_ids() if "pricing" in p)
    scripted_llm.push(f"The Team tier costs $79 per month [{pricing_id}] [not-a-real-unit].")

    reply = agent.ask("How much is the Team tier?")

    assert "$79" in reply.answer
    assert reply.citations == [pricing_id]          # bogus id filtered out
    assert pricing_id in reply.used_units            # retrieval found the section

    # the model actually received pack content + overview + question
    request = scripted_llm.seen[0]
    user_message = request["messages"][-1]["content"]
    assert "$79 per month" in user_message           # excerpt text
    assert "RESOURCE OVERVIEW" in user_message
    assert "How much is the Team tier?" in user_message
    system = request["messages"][0]["content"]
    assert "handbook" in system
    assert real_id  # sanity


def test_history_is_passed_through(handbook_pack, scripted_llm):
    agent = ResourceAgent(handbook_pack, scripted_llm.config())
    scripted_llm.push("second answer")
    history = [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]
    agent.ask("follow-up?", history=history)
    messages = scripted_llm.seen[0]["messages"]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "earlier question"


def test_agent_card(handbook_pack, scripted_llm):
    agent = ResourceAgent(handbook_pack, scripted_llm.config())
    card = agent.card()
    assert card["agent_id"] == "handbook"
    assert card["resource_type"] == "document"
    assert card["unit_count"] >= 4
    assert "ask" in card["capabilities"]


def test_peer_ask_roundtrip(handbook_pack, lecture_pack, scripted_llm):
    """Agent A consults agent B via the @ask protocol (in-process peer)."""
    config = scripted_llm.config()
    lecture_agent = ResourceAgent(lecture_pack, config)
    handbook_agent = ResourceAgent(
        handbook_pack, config,
        peers={"lecture": LocalPeer("lecture", lecture_agent)},
    )
    scripted_llm.push(
        "@ask lecture What does error code E42 mean?",       # A decides to ask B
        "E42 means the widget cache is stale.",               # B's answer (its own LLM call)
        "According to the lecture agent, E42 means the widget cache is stale.",  # A final
    )

    reply = handbook_agent.ask("What does E42 mean according to the lecture?")

    assert "cache is stale" in reply.answer
    assert reply.peer_calls and reply.peer_calls[0]["peer"] == "lecture"
    assert "E42" in reply.peer_calls[0]["question"]
    # third request (A's second turn) contains the peer answer as context
    final_request = scripted_llm.seen[-1]["messages"][-1]["content"]
    assert "PEER ANSWER from 'lecture'" in final_request
    # peer's own call must not recurse into peers (allow_peers=False)
    peer_request = scripted_llm.seen[1]["messages"][0]["content"]
    assert "@ask" not in peer_request.split("Peer agents")[0]


def test_unknown_peer_recovers(handbook_pack, lecture_pack, scripted_llm):
    config = scripted_llm.config()
    lecture_agent = ResourceAgent(lecture_pack, config)
    agent = ResourceAgent(
        handbook_pack, config,
        peers={"lecture": LocalPeer("lecture", lecture_agent)},
    )
    scripted_llm.push(
        "@ask nonexistent Where is the treasure?",
        "Answering from my own pack instead: rollbacks take under 30 seconds [handbook__002__deployment-guide].",
    )
    reply = agent.ask("How fast are rollbacks?")
    assert "30 seconds" in reply.answer
    assert reply.peer_calls == []  # failed dispatch is not recorded as a call


def test_peer_hop_budget(handbook_pack, lecture_pack, scripted_llm):
    config = scripted_llm.config()
    lecture_agent = ResourceAgent(lecture_pack, config)
    agent = ResourceAgent(
        handbook_pack, config,
        peers={"lecture": LocalPeer("lecture", lecture_agent)},
    )
    # A keeps asking peers forever: 3 @ask turns from A + 2 peer answers interleaved
    scripted_llm.push(
        "@ask lecture q1", "peer answer 1",
        "@ask lecture q2", "peer answer 2",
        "@ask lecture q3",
    )
    reply = agent.ask("loop forever please")
    assert len(reply.peer_calls) == 2  # hop budget stops the loop
    assert "peer-consultation limit" in reply.answer
