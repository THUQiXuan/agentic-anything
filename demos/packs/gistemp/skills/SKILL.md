---
name: gistemp
description: Agent-native resource pack for https://data.giss.nasa.gov/gistemp/data_v4.html (3 units captured; generated without LLM).
---

# gistemp

## Overview

This `dataset` pack is a structured capture of https://data.giss.nasa.gov/gistemp/data_v4.html made on 2026-07-11T00:00:00Z in `ingest` mode. It contains 3 evidence unit(s), an interface inventory, and markdown views an agent can read directly.

## Resource map

| page_id | type | title |
|---|---|---|
| `nasa-gistemp-global__001__nasa-gistemp-global-csv-overview` | table | nasa-gistemp-global.csv overview |
| `nasa-gistemp-global__002__nasa-gistemp-global-csv-rows-1-100` | table | nasa-gistemp-global.csv rows 1-100 |
| `nasa-gistemp-global__003__nasa-gistemp-global-csv-rows-101-148` | table | nasa-gistemp-global.csv rows 101-148 |

## Reading the pack

```bash
cat agent-pack.json                 # what's in this pack
cat site.json | python -m json.tool # page index + frontier
cat pages/nasa-gistemp-global__001__nasa-gistemp-global-csv-overview.md
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
