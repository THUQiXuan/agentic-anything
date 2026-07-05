<div align="center">

<img src="assets/agentic-anything-banner.png" alt="Agentic Anything" width="920">

# Agentic Anything

**Turn any website into an agent-native toolkit.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-78%20passing-brightgreen.svg)](tests/)

[English](README.md) | [中文](README_ZH.md)

</div>

---

Websites are built for human eyes. Agents deserve better: structured data instead of pixel-parsing, documented interfaces instead of guesswork, and ready-made tools instead of ad-hoc scraping.

**Agentic Anything** processes any website into three progressively richer, agent-native layers:

```
              build                skill                clify
 Any URL ────────────▶ Site Pack ─────────▶ SKILL.md ─────────▶ site CLI
            capture &      structured JSON+MD   usage guide for     zero-dependency
            distill        API surface          agents (any LLM     per-site command
                           HTML evidence        via OpenRouter)     line tool
                           screenshots*
```

1. **`build`** — crawls the site and distills every page into structured manifests (`pages/*.json`), readable markdown views (`pages/*.md`), a full **API surface inventory** (forms, endpoints found in JavaScript, OpenAPI specs, feeds, sitemaps, live network calls), plus raw HTML evidence and optional full-page **screenshots** for agents that want visual grounding.
2. **`skill`** — generates a `SKILL.md` that teaches an agent *how to use this specific site*: what's on it, which interfaces exist, concrete workflows, and honest caveats. Uses any OpenAI-compatible LLM (OpenRouter by default), with a fully deterministic `--no-llm` fallback.
3. **`clify`** — emits a **zero-dependency, site-specific CLI** (stdlib-only Python) over the pack: `search`, `page`, `apis`, `forms`, `form-curl`, same-origin `fetch` — every command with `--json` output for agent consumption.

The result: an agent can *read* the site like documentation, *query* it like a database, and *operate* it like a tool.

## Installation

```bash
pip install -e .                 # core: zero runtime dependencies
pip install -e '.[render]'       # + Playwright for JS rendering & screenshots
python -m playwright install chromium
```

Requires Python 3.10+. The core installation uses only the standard library.

## Quick start

```bash
# 1. Capture a website into a site pack (no API key needed)
agentic-anything build https://quotes.toscrape.com/ -o packs/quotes --max-pages 10

# 2. Generate the agent skill (uses OpenRouter; see "LLM configuration" below)
export OPENROUTER_API_KEY="sk-or-..."          # your own key
agentic-anything skill packs/quotes --language both   # SKILL.md + SKILL_ZH.md

# 3. Generate the site-specific CLI
agentic-anything clify packs/quotes
python packs/quotes/cli/quotes_toscrape_com_cli.py search "Einstein miracle"

# ... or do all three in one shot:
agentic-anything pack https://quotes.toscrape.com/ -o packs/quotes
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
| `build URL -o DIR` | Capture a site into a pack. Options: `--max-pages`, `--render`, `--screenshots`, `--allow-cross-origin`, `--ignore-robots`, `--no-html`, `--no-probe`, `--seed URL`, `--timeout` |
| `skill PACK` | Generate `skills/SKILL.md`. Options: `--model`, `--base-url`, `--language en\|zh\|both`, `--no-llm` |
| `clify PACK` | Generate `cli/<site>_cli.py` + its README |
| `pack URL -o DIR` | One-shot: build + skill + clify |
| `query PACK "question"` | Keyword search across the pack with evidence blocks |
| `page PACK PAGE_ID [--format md\|json]` | Print one captured page |
| `apis PACK` | Show the discovered API surface |
| `info PACK` | Pack summary |

All data-producing commands accept `--json`. `aany` is a short alias for `agentic-anything`.

## LLM configuration (OpenRouter & friends)

Skill generation talks to any **OpenAI-compatible** chat endpoint. Defaults target [OpenRouter](https://openrouter.ai) so one key unlocks every hosted model:

| Environment variable | Default | Meaning |
|---|---|---|
| `OPENROUTER_API_KEY` | — | API key (**required** for LLM features; never stored on disk) |
| `AGENTIC_API_KEY` | — | Alternative key name; takes precedence if both are set |
| `AGENTIC_MODEL` | `google/gemini-3.5-flash` | Any model id your endpoint serves |
| `AGENTIC_BASE_URL` | `https://openrouter.ai/api/v1` | Any OpenAI-compatible server (OpenAI, vLLM, llama.cpp, LM Studio, …) |

```bash
export OPENROUTER_API_KEY="sk-or-..."
agentic-anything skill packs/quotes --model anthropic/claude-sonnet-4.5   # pick any model
agentic-anything skill packs/quotes --no-llm                              # or no LLM at all
```

Everything except `skill` (and `pack`'s skill step) runs **without any API key**.

## Python API

```python
from agentic_anything import build_pack, generate_skill, generate_site_cli, search_pack
from agentic_anything.config import BuildConfig, LLMConfig

result = build_pack(
    "https://quotes.toscrape.com/",
    "packs/quotes",
    config=BuildConfig(max_pages=10, render=False),
)
generate_skill(result.pack_dir, llm_config=LLMConfig.from_env(), language="both")
generate_site_cli(result.pack_dir)

hits = search_pack(result.pack_dir, "login form fields", top=3)
```

## Testing

```bash
pip install -e '.[dev]'
python -m pytest tests -q        # 78 tests; rendered-mode tests auto-skip without Playwright
```

The suite covers the HTML parser, crawler policies (budget, robots.txt, same-site boundary, sitemap seeding), API discovery (forms, JS scanning, OpenAPI probing), pack building, search, skill generation (LLM stubbed + deterministic), the generated site CLI (run as a real subprocess), and the LLM client (against a local fake server). No test calls external services.

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
