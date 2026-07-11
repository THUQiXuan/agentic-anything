# Agentic Anything demo gallery

[Open the hosted demo](https://thuqixuan.github.io/agentic-anything/) ·
[inspect the raw results](results/showcase.json) ·
[read the main project documentation](../README.md)

This directory is a checked-in, reproducible snapshot of what the current
Agentic Anything code can do without an LLM or API key.

## Included demos

| Resource | Source | What the demo finds |
|---|---|---|
| Document | bilingual Markdown handbook | Chinese E42 remediation and rollback code |
| Video | SRT incident timeline | recovery time and incident sequence |
| Dataset | CSV service metrics | the AP South latency/incident row |
| Code | tiny Python repository | retry mode, timeout, and retry limit |
| Website | two-page local site | runbook ID, maintenance window, and form surface |

Every resource is committed in three forms:

1. `sources/` — the small synthetic input;
2. `packs/` — the actual agent-native pack, generated skill/CLI, interface
   manifest, and human entry guide;
3. `results/` — exact search, CLI, MCP, and verification transcripts consumed
   by the HTML gallery.

## Rebuild and verify

From the repository root:

```bash
python demos/build_demos.py
python demos/verify_demos.py
```

The builder removes `OPENROUTER_API_KEY` and `AGENTIC_API_KEY` from its child
processes. No credential, paid request, or model output is needed. To view the
page locally:

```bash
python -m http.server 8000 --directory demos
# open http://localhost:8000/
```

## Scope

These demos validate deterministic capture, structured evidence retrieval,
generated resource CLIs, stable interface manifests, and read-only MCP access.
They deliberately do not claim generative answer quality, human productivity,
perfect ingestion fidelity, or compatibility with every host.
