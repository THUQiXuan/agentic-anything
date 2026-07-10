"""Agentic Anything: turn anything into a chatable, agent-native resource.

The pipeline generalizes across resource types — websites, books (EPUB/PDF),
plain documents, video transcripts (SRT/VTT), or whole folders:

1. ``build``  - capture ANY source into a structured *pack* (non-visual,
                evidence-preserving units + API surface for websites).
2. ``chat``   - talk to the pack: a retrieval-grounded conversational agent
                with citations; agents can consult each other (A2A).
3. ``serve``  - host packs as agents over HTTP, including an OpenAI-compatible
                /v1/chat/completions endpoint (an agent per "model").
4. ``skill``  - generate a SKILL.md usage guide (LLM or deterministic).
5. ``clify``  - emit a zero-dependency, resource-specific CLI.
"""

from ._version import __version__  # noqa: E402
from .chat import AgentReply, HttpPeer, LocalPeer, ResourceAgent  # noqa: E402
from .ingest import build_pack_from_source  # noqa: E402
from .packer import build_pack  # noqa: E402
from .query import PackReader, search_pack  # noqa: E402
from .mcp import ResourceMCPServer  # noqa: E402
from .skills import generate_skill  # noqa: E402
from .sitecli import generate_site_cli  # noqa: E402

__all__ = [
    "__version__",
    "AgentReply",
    "HttpPeer",
    "LocalPeer",
    "ResourceAgent",
    "build_pack",
    "build_pack_from_source",
    "PackReader",
    "search_pack",
    "ResourceMCPServer",
    "generate_skill",
    "generate_site_cli",
]
