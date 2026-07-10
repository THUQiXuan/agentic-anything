"""Chat with a pack: every resource becomes a conversational agent.

``ResourceAgent`` wraps a built pack (website, book, video transcript,
document folder — anything ``build`` produced) and answers questions about
it with retrieval-grounded, citation-carrying replies.

Agents can also consult *peer agents* (other resources) through a simple
provider-agnostic protocol: when configured with peers, the model may reply
with a single line ``@ask <peer_id> <question>``; the engine intercepts it,
queries the peer (in-process or over HTTP), feeds the peer's answer back as
extra context, and asks the model to finish. This is how agent-to-agent
interaction works both inside one ``serve`` process and across servers.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .config import USER_AGENT, LLMConfig
from .llm import chat as llm_chat
from .query import PackReader, search_pack
from .util import truncate_text

_MAX_CONTEXT_CHARS = 24_000
_MAX_HISTORY_MESSAGES = 12
_MAX_PEER_HOPS = 2
# Single-line protocol: the WHOLE reply must be one '@ask <peer> <question>' line.
_ASK_RE = re.compile(r"^\s*@ask\s+([A-Za-z0-9_\-]+)\s+(.+?)\s*$")


@dataclass
class AgentReply:
    answer: str
    citations: list[str] = field(default_factory=list)
    used_units: list[str] = field(default_factory=list)
    peer_calls: list[dict] = field(default_factory=list)

    def as_json(self) -> dict:
        return {
            "answer": self.answer,
            "citations": self.citations,
            "used_units": self.used_units,
            "peer_calls": self.peer_calls,
        }


class Peer:
    """A peer agent the model may consult via ``@ask <id> <question>``."""

    def __init__(self, peer_id: str, description: str = "") -> None:
        self.peer_id = peer_id
        self.description = description

    def ask(self, question: str) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class LocalPeer(Peer):
    """Peer served by an agent object in the same process (used by `serve`)."""

    def __init__(self, peer_id: str, agent: "ResourceAgent", description: str = "") -> None:
        super().__init__(peer_id, description or agent.description)
        self._agent = agent

    def ask(self, question: str) -> str:
        return self._agent.ask(question, allow_peers=False).answer


class HttpPeer(Peer):
    """Peer reachable over the `serve` HTTP API (cross-process/machine)."""

    def __init__(self, peer_id: str, base_url: str, description: str = "",
                 timeout: float = 120.0) -> None:
        super().__init__(peer_id, description)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def ask(self, question: str) -> str:
        # allow_peers=false prevents unbounded A2A recursion across servers.
        body = json.dumps({"question": question, "allow_peers": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/agents/{self.peer_id}/ask",
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("answer", "")


class ResourceAgent:
    """A conversational agent embodied from one pack."""

    def __init__(
        self,
        pack_dir: str | Path,
        llm_config: LLMConfig,
        top_k: int = 6,
        peers: dict[str, Peer] | None = None,
        agent_id: str | None = None,
    ) -> None:
        self.reader = PackReader(pack_dir)
        self.llm_config = llm_config
        self.top_k = top_k
        self.peers = peers or {}
        site = self.reader.site
        self.agent_id = agent_id or site.get("site_id", "resource")
        self.resource_type = site.get("resource_type", "web")
        self.name = self.reader.discovery.get("site_name") or self.agent_id
        self._known_ids = set(self.reader.page_ids())

    # -- public card -------------------------------------------------------
    @property
    def description(self) -> str:
        site = self.reader.site
        pages = site.get("pages", [])
        sample = "; ".join(truncate_text(p.get("title", ""), 60) for p in pages[:4])
        return (
            f"{self.resource_type} resource '{self.name}' "
            f"({len(pages)} units; e.g. {sample})"
        )

    def card(self) -> dict:
        site = self.reader.site
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "resource_type": self.resource_type,
            "description": self.description,
            "unit_count": site.get("page_count"),
            "source": site.get("seed_url"),
            "captured_at": site.get("captured_at"),
            "capabilities": ["ask", "openai_chat_completions"],
            "peers": sorted(self.peers.keys()),
        }

    # -- retrieval ---------------------------------------------------------
    def _retrieve(self, question: str) -> tuple[str, list[str]]:
        hits = search_pack(self.reader, question, top=self.top_k)
        used: list[str] = []
        blocks: list[str] = []
        budget = _MAX_CONTEXT_CHARS
        per_unit = max(1200, budget // max(1, len(hits) or 1))
        for hit in hits:
            page_id = hit["page_id"]
            try:
                md = self.reader.page_markdown(page_id)
            except FileNotFoundError:
                continue
            used.append(page_id)
            blocks.append(f"--- excerpt [{page_id}] ---\n{truncate_text(md, per_unit)}")
        if not blocks:
            return "(no matching evidence units were retrieved)", []
        return "\n\n".join(blocks)[:_MAX_CONTEXT_CHARS], used

    def _overview(self) -> str:
        site = self.reader.site
        lines = [
            f"resource: {self.name} (type: {self.resource_type}, "
            f"source: {site.get('seed_url')}, captured: {site.get('captured_at')})",
            "unit index:",
        ]
        for page in site.get("pages", [])[:60]:
            lines.append(
                f"- [{page['page_id']}] {truncate_text(page.get('title', ''), 70)}"
            )
        frontier = site.get("frontier", [])
        if frontier:
            lines.append(f"(+{len(frontier)} discovered-but-uncaptured URLs; capture is partial)")
        return "\n".join(lines)

    # -- prompting ---------------------------------------------------------
    def _system_prompt(self, allow_peers: bool = True) -> str:
        prompt = f"""You are the conversational agent for one specific resource: {self.name}
(a {self.resource_type} captured as a structured pack). You ARE this resource's
interface — answer questions about its content faithfully.

Rules:
- Ground every claim in the provided excerpts. Cite unit ids in square
  brackets, e.g. [{next(iter(self._known_ids), 'index')}], after the claims they support.
- If the excerpts don't contain the answer, say so plainly and point to the
  closest related unit; never invent content.
- Quote exact wording when the user asks for specifics (prices, names, steps).
- Be concise and direct. Answer in the language of the question.
"""
        if allow_peers and self.peers:
            peer_lines = "\n".join(
                f"- {peer_id}: {peer.description}" for peer_id, peer in self.peers.items()
            )
            prompt += f"""
Peer agents you may consult (each is the agent of another resource):
{peer_lines}

If (and only if) the user's question needs information from a peer resource
rather than your own, reply with EXACTLY one line and nothing else:
@ask <peer_id> <question for that peer>
You will receive the peer's answer and can then respond to the user.
"""
        return prompt

    # -- main entry ----------------------------------------------------------
    def ask(
        self,
        question: str,
        history: list[dict] | None = None,
        allow_peers: bool = True,
    ) -> AgentReply:
        context, used = self._retrieve(question)
        overview = self._overview()
        peer_calls: list[dict] = []
        extra_context = ""

        for _hop in range(_MAX_PEER_HOPS + 1):
            user_message = (
                f"== RESOURCE OVERVIEW ==\n{overview}\n\n"
                f"== RETRIEVED EXCERPTS ==\n{context}\n"
                f"{extra_context}\n"
                f"== QUESTION ==\n{question}"
            )
            messages = list((history or [])[-_MAX_HISTORY_MESSAGES:])
            messages.append({"role": "user", "content": user_message})
            messages_with_system = [
                {"role": "system", "content": self._system_prompt(allow_peers)}
            ] + messages
            answer = llm_chat(messages_with_system, self.llm_config).strip()

            match = None
            if allow_peers and self.peers and "\n" not in answer:
                match = _ASK_RE.fullmatch(answer)
            if match is None:
                citations = self._extract_citations(answer)
                return AgentReply(
                    answer=answer,
                    citations=citations,
                    used_units=used,
                    peer_calls=peer_calls,
                )
            if len(peer_calls) >= _MAX_PEER_HOPS:
                break  # hop budget spent; don't dispatch another peer call

            peer_id, peer_question = match.group(1), match.group(2).strip()
            peer = self.peers.get(peer_id)
            if peer is None:
                extra_context += (
                    f"\n== PEER ERROR ==\nNo peer named '{peer_id}' exists. "
                    "Answer from your own excerpts instead.\n"
                )
                continue
            try:
                peer_answer = peer.ask(peer_question)
            except Exception as exc:
                peer_answer = f"(peer '{peer_id}' unreachable: {type(exc).__name__})"
            peer_calls.append(
                {"peer": peer_id, "question": peer_question,
                 "answer": truncate_text(peer_answer, 4000)}
            )
            extra_context += (
                f"\n== PEER ANSWER from '{peer_id}' "
                f"(you asked: {peer_question}) ==\n{truncate_text(peer_answer, 4000)}\n"
                "Now answer the user's original question yourself; mention that "
                f"this part came from the '{peer_id}' agent.\n"
            )

        # peer-hop budget exhausted — answer with what the peers said, without
        # leaking internal prompt scaffolding or mis-attributed citations.
        if peer_calls:
            last = peer_calls[-1]
            answer = (
                f"(peer-consultation limit reached) The '{last['peer']}' agent "
                f"answered my last question ({last['question']}) with: {last['answer']}"
            )
        else:
            answer = "I could not complete the peer consultation; please re-ask."
        return AgentReply(
            answer=answer,
            citations=[],
            used_units=used,
            peer_calls=peer_calls,
        )

    def _extract_citations(self, answer: str) -> list[str]:
        cited = re.findall(r"\[([A-Za-z0-9_\-~]+)\]", answer)
        seen: list[str] = []
        for page_id in cited:
            if page_id in self._known_ids and page_id not in seen:
                seen.append(page_id)
        return seen


# --------------------------------------------------------------------------
# interactive REPL used by the `chat` CLI command
# --------------------------------------------------------------------------

def run_chat_repl(agent: ResourceAgent) -> int:  # pragma: no cover - interactive
    import sys

    print(f"chatting with agent '{agent.agent_id}' ({agent.resource_type}: {agent.name})")
    if agent.peers:
        print(f"peers available: {', '.join(agent.peers)}")
    print("type your question; /reset clears history; /quit exits\n")
    history: list[dict] = []
    while True:
        try:
            question = input(f"[{agent.agent_id}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not question:
            continue
        if question in ("/quit", "/exit", "q"):
            return 0
        if question == "/reset":
            history = []
            print("(history cleared)")
            continue
        try:
            reply = agent.ask(question, history=history)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            continue
        print(f"\n{reply.answer}\n")
        if reply.citations:
            print(f"  citations: {', '.join(reply.citations)}")
        for call in reply.peer_calls:
            print(f"  (asked peer '{call['peer']}': {truncate_text(call['question'], 80)})")
        print()
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": reply.answer})
        history = history[-_MAX_HISTORY_MESSAGES:]
