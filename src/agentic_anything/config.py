"""Configuration for LLM access and capture behavior.

All LLM access goes through an OpenAI-compatible chat-completions endpoint.
The defaults target OpenRouter so users can call any hosted model with a
single key, but ``AGENTIC_BASE_URL`` accepts any compatible server
(OpenAI, vLLM, llama.cpp, LM Studio, ...).

Environment variables (never hardcode secrets; keys are read at runtime):

- ``OPENROUTER_API_KEY``  API key for the LLM endpoint (preferred name).
- ``AGENTIC_API_KEY``     Alternative key name; wins over OPENROUTER_API_KEY.
- ``AGENTIC_MODEL``       Chat model id (default: ``google/gemini-3.5-flash``).
- ``AGENTIC_BASE_URL``    OpenAI-compatible base URL
                          (default: ``https://openrouter.ai/api/v1``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from ._version import __version__

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "google/gemini-3.5-flash"
USER_AGENT = f"agentic-anything/{__version__} (+https://github.com/THUQiXuan/agentic-anything)"

# Sent to OpenRouter for app attribution (both optional, non-sensitive).
OPENROUTER_REFERER = "https://github.com/THUQiXuan/agentic-anything"
OPENROUTER_TITLE = "Agentic Anything"


@dataclass
class LLMConfig:
    api_key: str = ""
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    temperature: float = 0.3
    max_tokens: int = 8192
    timeout: float = 180.0
    retries: int = 3

    @classmethod
    def from_env(
        cls,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> "LLMConfig":
        key = (
            api_key
            or os.environ.get("AGENTIC_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or ""
        )
        return cls(
            api_key=key,
            model=model or os.environ.get("AGENTIC_MODEL", DEFAULT_MODEL),
            base_url=(base_url or os.environ.get("AGENTIC_BASE_URL", DEFAULT_BASE_URL)).rstrip("/"),
        )

    @property
    def available(self) -> bool:
        return bool(self.api_key)


@dataclass
class BuildConfig:
    """Options controlling ``build`` (capture + distill)."""

    max_pages: int = 20
    same_origin_only: bool = True
    respect_robots: bool = True
    timeout: float = 20.0
    render: bool = False               # use Playwright Chromium for JS pages
    screenshots: bool = False          # full-page PNG per page (requires render)
    sniff_network: bool = True         # record XHR/fetch API calls (render mode)
    include_html: bool = True          # keep captured HTML as evidence
    probe_well_known: bool = True      # probe /openapi.json, /.well-known/*, sitemap, feeds
    max_js_files: int = 8              # same-origin JS files scanned for endpoints
    max_js_bytes: int = 400_000        # per-file JS scan cap
    render_wait_ms: int = 1500
    extra_seeds: list[str] = field(default_factory=list)

    # Deep capture: follow links from crawled pages into non-HTML resources
    # and merge them into the same pack. 0 disables following (the links are
    # still recorded in the frontier instead of being dropped).
    follow_docs: int = 0               # linked documents/data files to ingest
    follow_repos: int = 0              # linked GitHub repositories to ingest
    follow_hosts: list[str] = field(default_factory=list)  # extra allowed hosts
    follow_max_bytes: int = 30_000_000  # per-attachment download cap
