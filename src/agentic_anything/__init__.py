"""Agentic Anything: turn any website into an agent-native toolkit.

The pipeline has three layers, each producing artifacts an agent can use
directly:

1. ``build``  - capture a website into a structured, non-visual *site pack*
                (page manifests, markdown views, API surface, optional
                screenshots as opt-in visual evidence).
2. ``skill``  - generate a SKILL.md usage guide for the site (LLM via any
                OpenAI-compatible endpoint such as OpenRouter, with a
                deterministic no-LLM fallback).
3. ``clify``  - emit a zero-dependency, site-specific CLI over the pack.
"""

from ._version import __version__  # noqa: E402
from .packer import build_pack  # noqa: E402
from .query import PackReader, search_pack  # noqa: E402
from .skills import generate_skill  # noqa: E402
from .sitecli import generate_site_cli  # noqa: E402

__all__ = [
    "__version__",
    "build_pack",
    "PackReader",
    "search_pack",
    "generate_skill",
    "generate_site_cli",
]
