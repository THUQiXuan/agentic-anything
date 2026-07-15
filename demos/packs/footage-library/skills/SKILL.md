---
name: footage-library
description: Agent-native resource pack for demos/sources/footage (10 units captured; generated without LLM).
---

# footage-library

## Overview

This `collection` pack is a structured capture of demos/sources/footage made on 2026-07-11T00:00:00Z in `ingest` mode. It contains 10 evidence unit(s), an interface inventory, and markdown views an agent can read directly.

## Resource map

| page_id | type | title |
|---|---|---|
| `elephants-dream-en-srt__elephants-dream-en__001__00-00-15` | segment | transcript 00:00:15–00:03:14 |
| `elephants-dream-en-srt__elephants-dream-en__002__00-03-18` | segment | transcript 00:03:18–00:06:19 |
| `elephants-dream-en-srt__elephants-dream-en__003__00-06-39` | segment | transcript 00:06:39–00:08:59 |
| `sintel-en-srt__sintel-en__001__00-01-47` | segment | transcript 00:01:47–00:04:28 |
| `sintel-en-srt__sintel-en__002__00-05-04` | segment | transcript 00:05:04–00:07:44 |
| `sintel-en-srt__sintel-en__003__00-09-17` | segment | transcript 00:09:17–00:10:29 |
| `tears-of-steel-en-srt__tears-of-steel-en__001__00-00-23` | segment | transcript 00:00:23–00:03:23 |
| `tears-of-steel-en-srt__tears-of-steel-en__002__00-03-23` | segment | transcript 00:03:23–00:06:25 |
| `tears-of-steel-en-srt__tears-of-steel-en__003__00-06-26` | segment | transcript 00:06:26–00:09:24 |
| `tears-of-steel-en-srt__tears-of-steel-en__004__00-09-26` | segment | transcript 00:09:26–00:09:27 |

## Reading the pack

```bash
cat agent-pack.json                 # what's in this pack
cat site.json | python -m json.tool # page index + frontier
cat pages/elephants-dream-en-srt__elephants-dream-en__001__00-00-15.md
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
