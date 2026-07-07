"""Agent HTTP server: directory, ask, OpenAI-compatible endpoint, A2A."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from agentic_anything.ingest import build_pack_from_source
from agentic_anything.server import AgentServer

RESOURCES = Path(__file__).parent / "fixtures" / "resources"


@pytest.fixture()
def two_packs(tmp_path):
    build_pack_from_source(str(RESOURCES / "handbook.md"), tmp_path / "handbook",
                           site_id="handbook")
    build_pack_from_source(str(RESOURCES / "lecture.srt"), tmp_path / "lecture",
                           site_id="lecture")
    return tmp_path / "handbook", tmp_path / "lecture"


@pytest.fixture()
def running_server(two_packs, scripted_llm):
    server = AgentServer(list(two_packs), scripted_llm.config(),
                         host="127.0.0.1", port=0, enable_a2a=True)
    server.start_background()
    yield server, scripted_llm
    server.shutdown()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(url: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_agent_directory(running_server):
    server, _ = running_server
    payload = _get(f"{server.base_url}/agents")
    ids = {card["agent_id"] for card in payload["agents"]}
    assert ids == {"handbook", "lecture"}
    handbook = next(c for c in payload["agents"] if c["agent_id"] == "handbook")
    assert handbook["resource_type"] == "document"
    assert handbook["peers"] == ["lecture"]  # a2a enabled

    card = _get(f"{server.base_url}/agents/lecture/card")
    assert card["resource_type"] == "video"

    index = _get(f"{server.base_url}/")
    assert "handbook" in index["agents"]


def test_ask_endpoint(running_server):
    server, llm = running_server
    from agentic_anything.query import PackReader

    handbook_agent = server.agents["handbook"]
    pricing_id = next(p for p in handbook_agent.reader.page_ids() if "pricing" in p)
    llm.push(f"The Team tier costs $79 per month [{pricing_id}].")
    status, payload = _post(
        f"{server.base_url}/agents/handbook/ask",
        {"question": "How much is the Team tier?"},
    )
    assert status == 200
    assert payload["agent"] == "handbook"
    assert "$79" in payload["answer"]
    assert payload["citations"] == [pricing_id]


def test_ask_errors(running_server):
    server, _ = running_server
    status, payload = _post(f"{server.base_url}/agents/nope/ask", {"question": "hi"})
    assert status == 404
    status, payload = _post(f"{server.base_url}/agents/handbook/ask", {})
    assert status == 400
    assert "question" in payload["error"]["message"]


def test_openai_compatible_endpoint(running_server):
    server, llm = running_server
    deploy_id = next(
        p for p in server.agents["handbook"].reader.page_ids() if "deployment" in p
    )
    llm.push(f"Rollbacks complete in under 30 seconds [{deploy_id}].")
    status, payload = _post(
        f"{server.base_url}/v1/chat/completions",
        {"model": "handbook",
         "messages": [
             {"role": "user", "content": "old question"},
             {"role": "assistant", "content": "old answer"},
             {"role": "user", "content": "How fast are rollbacks?"},
         ]},
    )
    assert status == 200
    assert payload["object"] == "chat.completion"
    assert payload["model"] == "handbook"
    assert "30 seconds" in payload["choices"][0]["message"]["content"]
    assert payload["agentic_anything"]["citations"] == [deploy_id]
    # history made it into the LLM request
    llm_messages = llm.seen[-1]["messages"]
    assert any(m["content"] == "old question" for m in llm_messages)

    models = _get(f"{server.base_url}/v1/models")
    assert {m["id"] for m in models["data"]} == {"handbook", "lecture"}


def test_openai_unknown_model(running_server):
    server, _ = running_server
    status, payload = _post(
        f"{server.base_url}/v1/chat/completions",
        {"model": "ghost", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert status == 404
    assert "handbook" in payload["error"]["message"]


def test_a2a_over_server(running_server):
    """handbook agent consults the co-hosted lecture agent."""
    server, llm = running_server
    llm.push(
        "@ask lecture What does E42 mean?",
        "E42 means the widget cache is stale.",
        "Per the lecture agent: E42 means the widget cache is stale.",
    )
    status, payload = _post(
        f"{server.base_url}/agents/handbook/ask",
        {"question": "What does the lecture say E42 means?"},
    )
    assert status == 200
    assert "cache is stale" in payload["answer"]
    assert payload["peer_calls"] and payload["peer_calls"][0]["peer"] == "lecture"


def test_duplicate_site_ids_get_suffixed(two_packs, scripted_llm, tmp_path):
    # host the same pack twice: second instance gets '-2'
    server = AgentServer([two_packs[0], two_packs[0]], scripted_llm.config(),
                         host="127.0.0.1", port=0)
    try:
        assert set(server.agents) == {"handbook", "handbook-2"}
    finally:
        server.shutdown()
