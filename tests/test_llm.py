"""LLM client behavior against a local fake OpenAI-compatible server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agentic_anything.config import LLMConfig
from agentic_anything.llm import LLMError, chat


class _FakeLLMHandler(BaseHTTPRequestHandler):
    behaviors: list[str] = []  # queue of per-request behaviors
    seen: list[dict] = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        type(self).seen.append(
            {"path": self.path, "auth": self.headers.get("Authorization", ""), "body": body}
        )
        behavior = type(self).behaviors.pop(0) if type(self).behaviors else "ok"
        if behavior == "429":
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'{"error": "rate limited"}')
            return
        if behavior == "empty":
            payload = {"choices": []}
        elif behavior == "parts":
            payload = {
                "choices": [{"message": {"content": [{"type": "text", "text": "part1 "},
                                                     {"type": "text", "text": "part2"}]}}]
            }
        else:
            payload = {"choices": [{"message": {"content": f"echo:{body['model']}"}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def fake_llm():
    _FakeLLMHandler.behaviors = []
    _FakeLLMHandler.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLLMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}/v1", _FakeLLMHandler
    server.shutdown()
    thread.join(timeout=5)


def _config(base_url, **kw):
    defaults = dict(api_key="test-key", model="test/model", base_url=base_url,
                    timeout=10.0, retries=1)
    defaults.update(kw)
    return LLMConfig(**defaults)


def test_chat_roundtrip(fake_llm):
    base, handler = fake_llm
    out = chat([{"role": "user", "content": "hi"}], _config(base))
    assert out == "echo:test/model"
    request = handler.seen[0]
    assert request["path"] == "/v1/chat/completions"
    assert request["auth"] == "Bearer test-key"
    assert request["body"]["messages"][0]["content"] == "hi"


def test_chat_retries_on_429(fake_llm):
    base, handler = fake_llm
    handler.behaviors = ["429", "ok"]
    out = chat([{"role": "user", "content": "hi"}], _config(base))
    assert out.startswith("echo:")
    assert len(handler.seen) == 2


def test_chat_content_parts(fake_llm):
    base, handler = fake_llm
    handler.behaviors = ["parts"]
    out = chat([{"role": "user", "content": "hi"}], _config(base))
    assert out == "part1 part2"


def test_chat_empty_choices_raises(fake_llm):
    base, handler = fake_llm
    handler.behaviors = ["empty", "empty"]
    with pytest.raises(LLMError):
        chat([{"role": "user", "content": "hi"}], _config(base, retries=0))


def test_chat_no_key():
    config = LLMConfig(api_key="", base_url="http://127.0.0.1:1/v1")
    with pytest.raises(LLMError, match="No API key"):
        chat([{"role": "user", "content": "hi"}], config)


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.delenv("AGENTIC_API_KEY", raising=False)
    monkeypatch.setenv("AGENTIC_MODEL", "some/model")
    monkeypatch.setenv("AGENTIC_BASE_URL", "https://example.com/v1/")
    config = LLMConfig.from_env()
    assert config.api_key == "or-key"
    assert config.model == "some/model"
    assert config.base_url == "https://example.com/v1"

    monkeypatch.setenv("AGENTIC_API_KEY", "agentic-key")
    assert LLMConfig.from_env().api_key == "agentic-key"

    assert LLMConfig.from_env(model="cli/model").model == "cli/model"
