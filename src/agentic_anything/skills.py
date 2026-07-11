"""SKILL.md generation: teach agents how to use a captured site.

Two modes:

- **LLM mode** (default when an API key is configured): condenses the pack
  into a context document and asks the model to write a complete SKILL.md
  following the CLI-Anything conventions (YAML frontmatter, usage sections,
  a "For AI Agents" contract).
- **Deterministic mode** (``--no-llm`` or no key): assembles the same
  sections directly from pack data. Less prose, still fully usable.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import LLMConfig
from .llm import chat
from .query import PackReader
from .util import truncate_text, utc_now_iso

_MAX_CONTEXT_CHARS = 60_000
_MAX_PAGE_MD = 8


def build_context_document(reader: PackReader) -> str:
    """Condense the pack into one context document for the LLM."""
    site = reader.site
    apis = reader.apis
    lines: list[str] = []
    lines.append(f"SITE: {site.get('site_id')}  seed={site.get('seed_url')}")
    lines.append(
        f"captured={site.get('captured_at')} mode={site.get('capture_mode')} "
        f"pages={site.get('page_count')} frontier={len(site.get('frontier', []))}"
    )
    lines.append("")
    lines.append("== PAGE INDEX ==")
    for page in site.get("pages", []):
        lines.append(
            f"- {page['page_id']} [{page.get('page_type')}] {page.get('url_path')} "
            f"| {truncate_text(page.get('title', ''), 80)} | {truncate_text(page.get('summary', ''), 140)}"
        )
    frontier = site.get("frontier", [])
    if frontier:
        lines.append("")
        lines.append(f"== NOT CAPTURED (frontier, {len(frontier)} urls) ==")
        for entry in frontier[:15]:
            lines.append(f"- {entry['url']} ({entry['skip_reason']})")

    lines.append("")
    lines.append("== API SURFACE ==")
    for form in apis.get("forms", []):
        fields = ", ".join(
            f"{f['name']}:{f['type']}{'*' if f.get('required') else ''}" for f in form.get("fields", [])
        )
        lines.append(
            f"- FORM {form['method']} {form['action_url']} (page={form['page_id']}) fields: {fields}"
        )
    for ep in apis.get("endpoints", []):
        lines.append(f"- ENDPOINT {ep['method']} {ep['url']} (source={ep['source']}) {ep.get('note', '')}")
    for ob in apis.get("observed_network", []):
        lines.append(
            f"- OBSERVED {ob['method']} {ob['url']} status={ob.get('status')} type={ob.get('response_content_type')}"
        )
    for spec in apis.get("openapi", []):
        lines.append(
            f"- OPENAPI {spec['url']} v{spec.get('version')} '{spec.get('title')}' paths: "
            + ", ".join(spec.get("paths", [])[:40])
        )
    for feed in apis.get("feeds", []):
        lines.append(f"- FEED {feed['url']} ({feed.get('type')})")
    for wk in apis.get("well_known", []):
        lines.append(f"- WELL-KNOWN {wk['url']}")
    for sm in apis.get("sitemaps", []):
        lines.append(f"- SITEMAP {sm['url']} ({sm['url_count']} urls)")

    lines.append("")
    lines.append("== REPRESENTATIVE PAGES (markdown views) ==")
    budget = _MAX_CONTEXT_CHARS - sum(len(l) + 1 for l in lines)
    pages = sorted(
        site.get("pages", []),
        key=lambda p: (p.get("page_type") == "content", p.get("depth", 0)),
    )[:_MAX_PAGE_MD]
    per_page = max(1500, budget // max(1, len(pages)))
    for page in pages:
        try:
            md = reader.page_markdown(page["page_id"])
        except FileNotFoundError:
            continue
        lines.append(f"\n--- page: {page['page_id']} ---")
        lines.append(truncate_text(md, per_page))

    doc = "\n".join(lines)
    return doc[:_MAX_CONTEXT_CHARS]


_SYSTEM_PROMPT = """\
You write SKILL.md files that teach AI agents how to use a specific resource
through its Agentic Anything pack. The resource may be a website, document,
book, video transcript, dataset, software tool, or code repository. The pack is
a structured, non-visual, evidence-preserving representation.

A SKILL.md must be plain Markdown with YAML frontmatter and EXACTLY these
sections, in order:

---
name: <resource-id>
description: <one sentence: what the resource contains and what an agent can do with it>
---

# <Resource name>

## Overview
2-4 sentences: what this resource is, what it contains, what tasks an agent can
accomplish with it.

## Resource map
A short table of the most important captured units: page_id | type | what it contains.
Mention notable uncaptured items (frontier) if any matter.

## Reading the pack
Explain the concrete file layout the agent should read:
- `agent-pack.json` (index), `site.json` (page index + frontier)
- `pages/<page_id>.md` (readable view) and `pages/<page_id>.json` (structured)
- `api/apis.json` (API surface), `html/`, `snapshots/` if present
Include 1-2 example shell commands (cat / python -m json.tool).

## Interfaces and actions
Document every usable interface found. For websites this may include forms,
API endpoints, feeds, or OpenAPI specs; for software and code it may include
commands or files. If none exist, say so and point to evidence units.

## Common workflows
2-4 realistic agent tasks on this resource, each as a short numbered recipe that
references concrete page_ids / endpoints / files from THIS pack.

## For AI Agents
A bullet contract: prefer pages/*.md for reading; use pages/*.json when you
  need structure; verify claims against provenance when stakes are high;
never invent actions not represented in the pack; respect access policy and
licenses; screenshots in snapshots/ are optional visual evidence.

## Caveats
Honest limits of this capture: units not captured, unsupported native
structure/actions, dynamic content, auth walls, and staleness.

Rules:
- Ground EVERY claim in the provided pack data. Never invent pages, fields, or
  endpoints. If data is missing, state that.
- Be concise and operational: commands and file paths over prose.
- Output ONLY the Markdown document. No preamble, no code fences around the
  whole document.
"""


def generate_skill(
    pack_dir: str | Path,
    llm_config: LLMConfig | None = None,
    use_llm: bool = True,
    language: str = "en",
) -> Path:
    """Generate skills/SKILL.md (and SKILL_ZH.md when language includes zh)."""
    reader = PackReader(pack_dir)
    skill_dir = reader.pack_dir / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)

    if use_llm and llm_config is not None and llm_config.available:
        context = build_context_document(reader)
        want_zh = language in ("zh", "both")
        want_en = language in ("en", "both")
        if want_en:
            content = _llm_skill(context, llm_config, "English")
            (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        if want_zh:
            content_zh = _llm_skill(context, llm_config, "Simplified Chinese")
            target = skill_dir / ("SKILL_ZH.md" if want_en else "SKILL.md")
            target.write_text(content_zh, encoding="utf-8")
    else:
        content = deterministic_skill(reader)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    return skill_dir / "SKILL.md"


def _llm_skill(context: str, llm_config: LLMConfig, language: str) -> str:
    user = (
        f"Write the SKILL.md in {language} for the following resource pack. "
        f"Frontmatter keys and section headings stay in English; body text in {language}.\n\n"
        f"{context}"
    )
    content = chat(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        llm_config,
    )
    return _clean_markdown(content)


def _clean_markdown(text: str) -> str:
    text = text.strip()
    # strip a single wrapping ```markdown ... ``` fence if the model added one
    match = re.match(r"^```(?:markdown|md)?\s*\n(.*)\n```$", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    if not text.startswith("---"):
        text = "---\nname: site\ndescription: generated skill\n---\n\n" + text
    return text + "\n"


def deterministic_skill(reader: PackReader) -> str:
    """No-LLM fallback: assemble SKILL.md sections straight from pack data."""
    site = reader.site
    apis = reader.apis
    site_id = site.get("site_id", "site")
    pages = site.get("pages", [])
    site_name = reader.discovery.get("site_name") or site_id

    lines: list[str] = []
    lines += [
        "---",
        f"name: {site_id}",
        f"description: Agent-native resource pack for {site.get('seed_url', site_id)} "
        f"({len(pages)} units captured; generated without LLM).",
        "---",
        "",
        f"# {site_name}",
        "",
        "## Overview",
        "",
        f"This `{site.get('resource_type', 'resource')}` pack is a structured capture of "
        f"{site.get('seed_url')} made on "
        f"{site.get('captured_at')} in `{site.get('capture_mode')}` mode. "
        f"It contains {len(pages)} evidence unit(s), an interface inventory, and markdown "
        "views an agent can read directly.",
        "",
        "## Resource map",
        "",
        "| page_id | type | title |",
        "|---|---|---|",
    ]
    for page in pages:
        lines.append(
            f"| `{page['page_id']}` | {page.get('page_type', '')} | {truncate_text(page.get('title', ''), 60)} |"
        )
    frontier = site.get("frontier", [])
    if frontier:
        lines += ["", f"{len(frontier)} additional URL(s) were discovered but not captured (see `site.json` → `frontier`)."]

    lines += [
        "",
        "## Reading the pack",
        "",
        "```bash",
        "cat agent-pack.json                 # what's in this pack",
        "cat site.json | python -m json.tool # page index + frontier",
        f"cat pages/{pages[0]['page_id']}.md" if pages else "ls pages/",
        "cat api/apis.json                   # every discovered interface",
        "```",
        "",
        "- `pages/<page_id>.md` — human/agent-readable view of each page",
        "- `pages/<page_id>.json` — structured manifest (content, links, forms, provenance)",
        "- `html/<page_id>.html` — captured HTML evidence" if "html_evidence" in reader.discovery.get("capabilities", []) else "",
        "- `snapshots/<page_id>.png` — full-page screenshots" if "visual_snapshots" in reader.discovery.get("capabilities", []) else "",
        "",
        "## Interfaces and actions",
        "",
    ]
    forms = apis.get("forms", [])
    endpoints = apis.get("endpoints", []) + apis.get("observed_network", [])
    if forms:
        for form in forms:
            fields = ", ".join(
                f"`{f['name']}`:{f['type']}{' (required)' if f.get('required') else ''}"
                for f in form.get("fields", [])
            )
            lines.append(f"- **Form** `{form['method']} {form['action_url']}` (page `{form['page_id']}`): {fields}")
    if endpoints:
        for ep in endpoints[:30]:
            lines.append(f"- **Endpoint** `{ep['method']} {ep['url']}` (source: {ep.get('source')})")
    for spec in apis.get("openapi", []):
        lines.append(f"- **OpenAPI spec**: {spec['url']} ({len(spec.get('paths', []))} paths)")
    for feed in apis.get("feeds", []):
        lines.append(f"- **Feed**: {feed['url']}")
    if not (forms or endpoints or apis.get("openapi") or apis.get("feeds")):
        lines.append("No machine interfaces were discovered; use page content in `pages/`.")

    lines += [
        "",
        "## Common workflows",
        "",
        "1. **Answer a question about the site**: search markdown views "
        "(`grep -ril '<keyword>' pages/`), read the matching `pages/<id>.md`.",
        "2. **Inspect a specific page**: `cat pages/<page_id>.json` for structure, "
        "links and forms with provenance.",
        "3. **Call an interface**: pick an entry from `api/apis.json`, then use the "
        "documented method + URL (verify with the site's terms first).",
        "",
        "## For AI Agents",
        "",
        "- Prefer `pages/*.md` for reading; switch to `pages/*.json` when you need structure.",
        "- Never invent endpoints: only those in `api/apis.json` are evidenced.",
        "- Cross-check important claims against `html/` evidence when present.",
        "- `site.json` → `frontier` lists what exists but was NOT captured.",
        "- Respect the site's robots.txt and terms of service for live calls.",
        "",
        "## Caveats",
        "",
        f"- Captured {site.get('captured_at')}; content may have changed since.",
        f"- Page budget was {site.get('max_pages')}; {len(frontier)} known URL(s) were left uncaptured.",
        "- Generated without an LLM (deterministic mode): descriptions are terse; "
        "regenerate with an OPENROUTER_API_KEY for richer guidance.",
    ]
    if site.get("capture_mode") == "static":
        lines.append("- Static capture: JavaScript-rendered content may be missing (rebuild with `--render`).")

    return "\n".join(l for l in lines if l is not None) + "\n"
