---
name: incident
description: Agent-native resource pack for https://github.com/THUQiXuan/agentic-anything/blob/main/demos/sources/incident.srt (3 units captured; generated without LLM).
---

# incident

## Overview

This `video` pack is a structured capture of https://github.com/THUQiXuan/agentic-anything/blob/main/demos/sources/incident.srt made on 2026-07-11T00:00:00Z in `ingest` mode. It contains 3 evidence unit(s), an interface inventory, and markdown views an agent can read directly.

## Resource map

| page_id | type | title |
|---|---|---|
| `incident__001__00-00-01` | segment | transcript 00:00:01–00:00:18 |
| `incident__002__00-03-30` | segment | transcript 00:03:30–00:03:56 |
| `incident__003__00-07-00` | segment | transcript 00:07:00–00:07:25 |

## Reading the pack

```bash
cat agent-pack.json                 # what's in this pack
cat site.json | python -m json.tool # page index + frontier
cat pages/incident__001__00-00-01.md
cat api/apis.json                   # every discovered interface
```

- `pages/<page_id>.md` — human/agent-readable view of each page
- `pages/<page_id>.json` — structured manifest (content, links, forms, provenance)



## Interfaces and actions

No machine interfaces were discovered; use page content in `pages/`.

## Common workflows

1. **Answer a question about the site**: search markdown views (`grep -ril '<keyword>' pages/`), read the matching `pages/<id>.md`.
2. **Inspect a specific page**: `cat pages/<page_id>.json` for structure, links and forms with provenance.
3. **Call an interface**: pick an entry from `api/apis.json`, then use the documented method + URL (verify with the site's terms first).

## For AI Agents

- Prefer `pages/*.md` for reading; switch to `pages/*.json` when you need structure.
- Never invent endpoints: only those in `api/apis.json` are evidenced.
- Cross-check important claims against `html/` evidence when present.
- `site.json` → `frontier` lists what exists but was NOT captured.
- Respect the site's robots.txt and terms of service for live calls.

## Caveats

- Captured 2026-07-11T00:00:00Z; content may have changed since.
- Page budget was None; 0 known URL(s) were left uncaptured.
- Generated without an LLM (deterministic mode): descriptions are terse; regenerate with an OPENROUTER_API_KEY for richer guidance.
