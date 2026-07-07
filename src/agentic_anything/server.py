"""Serve packs as chatable agents over HTTP (stdlib only).

Endpoints:

- ``GET  /agents``                    directory of hosted agent cards
- ``GET  /agents/<id>/card``          one agent card
- ``POST /agents/<id>/ask``           ``{"question": "...", "history": [...]}``
                                      → ``{"agent", "answer", "citations", ...}``
- ``POST /v1/chat/completions``       OpenAI-compatible; ``model`` selects the
                                      agent, so ANY OpenAI client or agent
                                      framework can talk to a resource agent —
                                      and agents can use each other as models.

With ``--enable-a2a`` every hosted agent gets all co-hosted agents as peers,
so one agent can answer questions that require another resource's content
(the ``@ask`` protocol in :mod:`agentic_anything.chat`).
"""

from __future__ import annotations

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ._version import __version__
from .chat import LocalPeer, ResourceAgent
from .config import LLMConfig

_AGENT_PATH_RE = re.compile(r"^/agents/([A-Za-z0-9_\-~.]+)(/card|/ask)?$")

_MAX_HISTORY_ITEMS = 40


def _sanitize_history(raw) -> list[dict] | None:
    """Validate/normalize a client-supplied history list; None if invalid."""
    if not isinstance(raw, list):
        return None
    out: list[dict] = []
    for item in raw[-_MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            return None
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            return None
        out.append({"role": role, "content": content})
    return out


class AgentServer:
    """Hosts one or more ResourceAgents behind a threaded HTTP server."""

    def __init__(
        self,
        pack_dirs: list[str | Path],
        llm_config: LLMConfig,
        host: str = "127.0.0.1",
        port: int = 8373,
        enable_a2a: bool = False,
        top_k: int = 6,
    ) -> None:
        self.llm_config = llm_config
        self.agents: dict[str, ResourceAgent] = {}
        for pack_dir in pack_dirs:
            agent = ResourceAgent(pack_dir, llm_config, top_k=top_k)
            agent_id = agent.agent_id
            if agent_id in self.agents:  # two packs with the same site_id
                n = 2
                while f"{agent_id}-{n}" in self.agents:
                    n += 1
                agent_id = f"{agent_id}-{n}"
                agent.agent_id = agent_id
            self.agents[agent_id] = agent

        if enable_a2a and len(self.agents) > 1:
            for agent_id, agent in self.agents.items():
                agent.peers = {
                    other_id: LocalPeer(other_id, other)
                    for other_id, other in self.agents.items()
                    if other_id != agent_id
                }

        handler = _make_handler(self)
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self.host, self.port = self.httpd.server_address[0], self.httpd.server_address[1]
        self._loop_started = False

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def serve_forever(self) -> None:  # pragma: no cover - blocking loop
        self._loop_started = True
        self.httpd.serve_forever()

    def start_background(self) -> threading.Thread:
        self._loop_started = True
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        return thread

    def shutdown(self) -> None:
        # socketserver.shutdown() deadlocks if serve_forever() never ran.
        if self._loop_started:
            self.httpd.shutdown()
        self.httpd.server_close()


def _make_handler(server: AgentServer):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args) -> None:  # keep stdout clean
            pass

        # -- helpers -------------------------------------------------------
        def _send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: int, message: str) -> None:
            self._send_json({"error": {"message": message, "code": status}}, status)

        def _read_body(self) -> dict | None:
            try:
                length = int(self.headers.get("Content-Length", 0))
                if length <= 0 or length > 2_000_000:
                    return {}
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return None

        # -- GET -----------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index", "/health"):
                self._send_json({
                    "service": "agentic-anything agent server",
                    "version": __version__,
                    "agents": sorted(server.agents.keys()),
                    "endpoints": ["/agents", "/agents/<id>/card", "/agents/<id>/ask",
                                  "/v1/chat/completions", "/v1/models"],
                })
                return
            if self.path == "/agents":
                self._send_json({
                    "agents": [agent.card() for agent in server.agents.values()]
                })
                return
            if self.path == "/v1/models":
                self._send_json({
                    "object": "list",
                    "data": [
                        {"id": agent_id, "object": "model",
                         "owned_by": "agentic-anything"}
                        for agent_id in server.agents
                    ],
                })
                return
            match = _AGENT_PATH_RE.match(self.path)
            if match and match.group(2) in (None, "/card"):
                agent = server.agents.get(match.group(1))
                if agent is None:
                    self._error(404, f"no agent '{match.group(1)}'")
                    return
                self._send_json(agent.card())
                return
            self._error(404, f"unknown path {self.path}")

        # -- POST ----------------------------------------------------------
        def do_POST(self) -> None:  # noqa: N802
            body = self._read_body()
            if body is None:
                self._error(400, "request body must be JSON")
                return

            match = _AGENT_PATH_RE.match(self.path)
            if match and match.group(2) == "/ask":
                self._handle_ask(match.group(1), body)
                return
            if self.path == "/v1/chat/completions":
                self._handle_openai(body)
                return
            self._error(404, f"unknown path {self.path}")

        def _handle_ask(self, agent_id: str, body: dict) -> None:
            agent = server.agents.get(agent_id)
            if agent is None:
                self._error(404, f"no agent '{agent_id}'")
                return
            question = (body.get("question") or "").strip()
            if not question:
                self._error(400, "missing 'question'")
                return
            history = _sanitize_history(body.get("history") or [])
            if history is None:
                self._error(400, "'history' must be a list of {role, content}")
                return
            allow_peers = bool(body.get("allow_peers", True))
            try:
                reply = agent.ask(question, history=history, allow_peers=allow_peers)
            except Exception as exc:
                self._error(502, f"agent failed: {type(exc).__name__}: {exc}")
                return
            self._send_json({"agent": agent_id, **reply.as_json()})

        def _handle_openai(self, body: dict) -> None:
            agent_id = body.get("model", "")
            agent = server.agents.get(agent_id)
            if agent is None:
                available = ", ".join(sorted(server.agents.keys()))
                self._error(
                    404,
                    f"unknown model '{agent_id}'; hosted agents: {available}",
                )
                return
            messages = body.get("messages") or []
            if not isinstance(messages, list) or not messages:
                self._error(400, "missing 'messages'")
                return
            question = ""
            history: list[dict] = []
            for message in messages:
                role = message.get("role") if isinstance(message, dict) else None
                content = message.get("content") if isinstance(message, dict) else None
                if isinstance(content, list):  # content-parts form
                    content = "".join(
                        part.get("text", "") for part in content
                        if isinstance(part, dict)
                    )
                if not isinstance(content, str):
                    content = "" if content is None else str(content)
                if role in ("user", "assistant"):
                    history.append({"role": role, "content": content})
            # The question is the LAST user turn; remove exactly that element
            # (clients may append an assistant prefill after it).
            user_indices = [i for i, m in enumerate(history) if m["role"] == "user"]
            if not user_indices:
                self._error(400, "no user message found")
                return
            last_user = user_indices[-1]
            question = history[last_user]["content"]
            history = history[:last_user]
            if not question.strip():
                self._error(400, "no user message found")
                return
            try:
                reply = agent.ask(question, history=history)
            except Exception as exc:
                self._error(502, f"agent failed: {type(exc).__name__}: {exc}")
                return
            self._send_json({
                "id": f"agentchat-{int(time.time() * 1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": agent_id,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": reply.answer},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "agentic_anything": {
                    "citations": reply.citations,
                    "used_units": reply.used_units,
                    "peer_calls": reply.peer_calls,
                },
            })

    return Handler
