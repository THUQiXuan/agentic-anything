<div align="center">

<img src="assets/agentic-anything-banner.png" alt="Agentic Anything" width="920">

# Agentic Anything

**Turn anything — websites, books, videos, documents — into a chatable, agent-native resource.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-121%20passing-brightgreen.svg)](tests/)

[English](README.md) | [中文](README_ZH.md)

</div>

---

Resources are built for human consumption. Agents deserve better: structured data instead of pixel-parsing, documented interfaces instead of guesswork, and — above all — **a conversation** instead of a scraping session.

**Agentic Anything** turns any resource into an agent:

```
  website ─┐                       ┌─ chat   talk to it (grounded answers + citations)
  book ────┤                       ├─ serve  host it as an HTTP agent; agents call
  video ───┼──▶ build ──▶ PACK ──▶ │         each other (A2A) & OpenAI-compatible API
  docs ────┤     capture &         ├─ skill  SKILL.md usage guide for agents
  folder ──┘     distill           └─ clify  zero-dependency per-resource CLI
```

- **`build`** — captures ANY source into a structured *pack*:
  - **websites**: same-site crawl, structured manifests, markdown views, full **API surface inventory** (forms, JS endpoints, OpenAPI, feeds, observed network calls), HTML evidence, optional screenshots;
  - **books**: EPUB chapters (stdlib zip + built-in HTML parser), PDF (`[docs]` extra);
  - **videos**: SRT/VTT transcripts split into time-coded segments;
  - **documents & folders**: Markdown by sections, plain text by passages, whole directories as collections.
- **`chat`** — the pack becomes a conversational agent: retrieval-grounded answers with unit citations (`[page_id]`), honest "not in my resource" refusals, multi-turn history — in your terminal or one-shot with `--ask`.
- **`serve`** — hosts packs as agents over HTTP: an `/agents` directory with agent cards, `POST /agents/<id>/ask`, and an **OpenAI-compatible `/v1/chat/completions`** where each agent is a "model" — so any agent framework can talk to your resources, and **agents can consult each other** (`--enable-a2a`, or `chat --peer id=url` across servers).
- **`skill`** / **`clify`** — generate a SKILL.md usage guide and a zero-dependency per-resource CLI (see below).

The result: an agent (or you) can *chat* with a website, *interview* a book, *query* a lecture video — and resource-agents can answer each other's questions over an API.

## Installation

```bash
pip install -e .                 # core: zero runtime dependencies
pip install -e '.[render]'       # + Playwright for JS rendering & screenshots
pip install -e '.[docs]'         # + pypdf for PDF ingestion
python -m playwright install chromium
```

Requires Python 3.10+. The core installation uses only the standard library.

## Quick start

```bash
# 1. Agentify ANY resource (no API key needed for capture)
agentic-anything build https://quotes.toscrape.com/ -o packs/quotes --max-pages 10
agentic-anything build alice.txt        -o packs/alice      # a book
agentic-anything build lecture.srt      -o packs/lecture    # a video transcript
agentic-anything build ./my-docs/       -o packs/docs       # a whole folder

# 2. Chat with it (any OpenAI-compatible LLM; OpenRouter by default)
export OPENROUTER_API_KEY="sk-or-..."
agentic-anything chat packs/alice                             # interactive REPL
agentic-anything chat packs/lecture --ask "What does E42 mean?"

# 3. Host resources as agents; let them talk to each other
agentic-anything serve packs/alice packs/lecture --port 8373 --enable-a2a
curl localhost:8373/agents                                    # agent directory
curl -X POST localhost:8373/agents/alice/ask \
     -d '{"question": "According to the lecture agent, what is E42?"}'
# ...alice consults the lecture agent over the @ask protocol and answers.

# Any OpenAI client can talk to a resource agent (model = agent id):
curl -X POST localhost:8373/v1/chat/completions \
     -d '{"model": "lecture", "messages": [{"role":"user","content":"Summarize the video"}]}'

# 4. Classic toolkit layers still apply to every pack
agentic-anything skill packs/quotes --language both   # SKILL.md + SKILL_ZH.md
agentic-anything clify packs/quotes                   # zero-dependency site CLI
agentic-anything pack  https://books.toscrape.com/    # build+skill+clify in one shot
```

For JavaScript-heavy sites, add rendering and visual snapshots:

```bash
agentic-anything build https://quotes.toscrape.com/js/ -o packs/quotes-js \
    --render --screenshots
```

Rendered mode also **sniffs the network**: every XHR/fetch API call the page makes is recorded into the pack's API surface — real endpoints, observed, not guessed.

## What a site pack looks like

```
packs/quotes/
├── agent-pack.json          # discovery document: what's in this pack
├── site.json                # page index + crawl frontier (what was NOT captured, and why)
├── pages/
│   ├── index.json           # structured manifest: content, links, forms, provenance
│   └── index.md             # the same page as agent-readable markdown
├── html/index.html          # captured HTML evidence
├── snapshots/index.png      # full-page screenshots (rendered mode, optional)
├── api/apis.json            # forms · JS endpoints · OpenAPI · feeds · observed network calls
├── skills/SKILL.md          # generated usage guide for agents (+ SKILL_ZH.md)
└── cli/quotes_..._cli.py    # generated zero-dependency site CLI
```

Design principles (inherited from the projects that inspired this one — see
[Acknowledgements](#acknowledgements)):

- **Non-visual first**: agents read markdown and JSON, not rendered pixels. Screenshots are available but opt-in.
- **Evidence preserved**: every manifest links back to captured HTML with a SHA-256; claims are verifiable.
- **Honest boundaries**: the crawl frontier records every URL that was discovered but *not* captured, with the reason (budget, robots.txt, cross-site, fetch error).
- **Agent-contract CLI**: everything supports `--json`, exit codes are meaningful, errors go to stderr.

## CLI reference

| Command | What it does |
|---|---|
| `build SOURCE -o DIR` | Agentify a source: URL, `.txt` `.md` `.epub` `.pdf` `.srt` `.vtt` `.html`, or a folder. Web options: `--max-pages`, `--render`, `--screenshots`, `--allow-cross-origin`, `--ignore-robots`, `--no-html`, `--no-probe`, `--seed URL`, `--timeout` |
| `chat PACK [--ask Q]` | Converse with the pack (REPL or one-shot). Options: `--top-k`, `--model`, `--base-url`, `--peer ID=URL` (consult remote agents), `--json` |
| `serve PACK... ` | Host packs as HTTP agents. Options: `--host`, `--port`, `--enable-a2a`, `--model`, `--top-k` |
| `skill PACK` | Generate `skills/SKILL.md`. Options: `--model`, `--base-url`, `--language en\|zh\|both`, `--no-llm` |
| `clify PACK` | Generate `cli/<site>_cli.py` + its README |
| `pack SOURCE -o DIR` | One-shot: build + skill + clify |
| `query PACK "question"` | Keyword search across the pack with evidence blocks |
| `page PACK PAGE_ID [--format md\|json]` | Print one captured unit |
| `apis PACK` | Show the discovered API surface (websites) |
| `info PACK` | Pack summary |

All data-producing commands accept `--json`. `aany` is a short alias for `agentic-anything`.

## Agent server API

`serve` exposes every pack as an agent:

| Endpoint | Description |
|---|---|
| `GET /agents` | Directory of hosted agents (cards: id, type, description, peers) |
| `GET /agents/<id>/card` | One agent card |
| `POST /agents/<id>/ask` | `{"question", "history"?}` → `{"answer", "citations", "used_units", "peer_calls"}` |
| `POST /v1/chat/completions` | OpenAI-compatible; `model` = agent id; citations returned under `agentic_anything` |
| `GET /v1/models` | Hosted agents as OpenAI models |

With `--enable-a2a`, co-hosted agents may consult each other: when an agent
decides another resource holds the answer, it emits `@ask <peer> <question>`,
the engine routes it (in-process or over HTTP via `chat --peer`), and the
final answer attributes what came from which agent (`peer_calls` in the
response). Hops are budgeted to prevent loops.

## LLM configuration (OpenRouter & friends)

`chat`, `serve` and skill generation talk to any **OpenAI-compatible** chat endpoint. Defaults target [OpenRouter](https://openrouter.ai) so one key unlocks every hosted model:

| Environment variable | Default | Meaning |
|---|---|---|
| `OPENROUTER_API_KEY` | — | API key (**required** for LLM features; never stored on disk) |
| `AGENTIC_API_KEY` | — | Alternative key name; takes precedence if both are set |
| `AGENTIC_MODEL` | `google/gemini-3.5-flash` | Any model id your endpoint serves |
| `AGENTIC_BASE_URL` | `https://openrouter.ai/api/v1` | Any OpenAI-compatible server (OpenAI, vLLM, llama.cpp, LM Studio, …) |

```bash
export OPENROUTER_API_KEY="sk-or-..."
agentic-anything chat  packs/alice  --model anthropic/claude-sonnet-4.5  # pick any model
agentic-anything skill packs/quotes --no-llm                             # or no LLM at all
```

Capture (`build`), search (`query`) and the generated CLIs run **without any API key**.

## Python API

```python
from agentic_anything import (
    ResourceAgent, build_pack, build_pack_from_source,
    generate_skill, generate_site_cli, search_pack,
)
from agentic_anything.config import BuildConfig, LLMConfig

# agentify a website ...
build_pack("https://quotes.toscrape.com/", "packs/quotes",
           config=BuildConfig(max_pages=10))
# ... or anything else
build_pack_from_source("alice.txt", "packs/alice")

# chat with it
agent = ResourceAgent("packs/alice", LLMConfig.from_env())
reply = agent.ask("How does Alice enter the rabbit hole?")
print(reply.answer, reply.citations)

# host agents programmatically
from agentic_anything.server import AgentServer
server = AgentServer(["packs/alice", "packs/quotes"], LLMConfig.from_env(),
                     port=8373, enable_a2a=True)
server.serve_forever()
```

## Testing

```bash
pip install -e '.[dev]'
python -m pytest tests -q        # 121 tests; rendered-mode tests auto-skip without Playwright
```

The suite covers the HTML parser, crawler policies (budget, robots.txt, same-site boundary, sitemap seeding), API discovery (forms, JS scanning, OpenAPI probing), non-web ingestion (markdown/text/EPUB/SRT/folders), pack building, search, the chat agent (retrieval grounding, citations, peer @ask protocol, hop budgets — against a scripted local LLM), the agent server (directory, ask, OpenAI-compatible endpoint, A2A), skill generation, the generated site CLI (run as a real subprocess), and the LLM client. No test calls external services.

## Responsible use

- robots.txt is respected by default (`--ignore-robots` exists for sites you own).
- Crawling is same-site and budget-limited by default.
- The generated site CLI's `fetch` command is restricted to same-origin GETs.
- Review a site's terms of service before building packs of it, and before letting agents call its endpoints.

## Acknowledgements

Agentic Anything stands on ideas from:

- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) — the SKILL.md contract, `--json`-everywhere CLI conventions, and the "make software agent-native" thesis.
- **web-anything** — evidence-preserving site bundles, crawl frontiers, and non-visual page manifests.
- [AutoFigure-Edit](https://github.com/ResearAI/AutoFigure-Edit) — used to generate the banner figure.

## License

[MIT](LICENSE)
