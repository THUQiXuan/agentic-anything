"""Minimal OpenAI-compatible chat client (stdlib only).

Defaults target OpenRouter; any compatible endpoint works via
``AGENTIC_BASE_URL``. The API key is read from the environment at runtime
and is never written to disk by this package.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .config import OPENROUTER_REFERER, OPENROUTER_TITLE, LLMConfig


class LLMError(RuntimeError):
    pass


def chat(
    messages: list[dict],
    config: LLMConfig,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Send a chat-completions request and return the assistant text."""
    if not config.api_key:
        raise LLMError(
            "No API key configured. Set OPENROUTER_API_KEY (or AGENTIC_API_KEY) "
            "in your environment, e.g.:  export OPENROUTER_API_KEY=sk-or-..."
        )
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature if temperature is None else temperature,
        "max_tokens": config.max_tokens if max_tokens is None else max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    url = f"{config.base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        # OpenRouter attribution headers (harmless on other endpoints).
        "HTTP-Referer": OPENROUTER_REFERER,
        "X-Title": OPENROUTER_TITLE,
    }

    last_error = ""
    for attempt in range(config.retries + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=config.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices") or []
            if not choices:
                raise LLMError(f"Empty response from model: {json.dumps(data)[:500]}")
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            if isinstance(content, list):  # some providers return content parts
                content = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            if not content.strip():
                raise LLMError("Model returned empty content")
            return content
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read(2000).decode("utf-8", errors="replace")
            except Exception:
                pass
            if exc.code in (429, 500, 502, 503, 504) and attempt < config.retries:
                time.sleep(2.0 * (attempt + 1))
                last_error = f"HTTP {exc.code}: {detail[:300]}"
                continue
            raise LLMError(f"LLM request failed (HTTP {exc.code}): {detail[:500]}") from exc
        except LLMError:
            raise
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < config.retries:
                time.sleep(2.0 * (attempt + 1))
                continue
    raise LLMError(f"LLM request failed after {config.retries + 1} attempts: {last_error}")
