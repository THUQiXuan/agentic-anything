"""Agentic Anything: turn any resource into an agent-native pack and agent.

The pipeline generalizes across resource types — websites, books (EPUB/PDF),
plain documents, video transcripts (SRT/VTT), or whole folders:

1. ``agentify`` - capture ANY source into an agent-native representation and
                  generate a discoverable resource-agent interface.
2. ``build``  - create the evidence-preserving pack representation only.
3. ``mcp``    - expose packs as read-only resources/tools/prompts to any MCP host.
4. ``chat``   - talk to the pack: a retrieval-grounded conversational agent
                with citations; agents can consult each other (A2A).
5. ``serve``  - host packs as agents over HTTP, including an OpenAI-compatible
                /v1/chat/completions endpoint (an agent per "model").
6. ``skill``  - generate a SKILL.md usage guide (LLM or deterministic).
7. ``clify``  - emit a zero-dependency, resource-specific CLI.
"""

from ._version import __version__  # noqa: E402
from .chat import AgentReply, HttpPeer, LocalPeer, ResourceAgent  # noqa: E402
from .ingest import build_pack_from_source  # noqa: E402
from .interface import generate_agent_interface  # noqa: E402
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
    "generate_agent_interface",
]
