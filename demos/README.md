# Agentic Anything authentic-source showcase

[Open the hosted walkthrough](https://thuqixuan.github.io/agentic-anything/) ·
[inspect the raw results](results/showcase.json) ·
[audit the source manifest](sources/real-sources.json) ·
[read the main project documentation](../README.md)

This directory is a checked-in, reproducible walkthrough built from real
external resources. No source passage, code file, table row, or book chapter
was invented for the demo.

## What the walkthrough proves

The flagship case traces the Requests redirect limit through three pieces of
the real `v2.34.2` repository: the constant definition, `Session` default, and
runtime guard. The transformation lab then applies the same contract to five
different native formats:

| Resource | Publisher and pinned version | Checked question |
|---|---|---|
| Code repository | PSF Requests `v2.34.2` | redirect ceiling and enforcement |
| Book | Project Gutenberg eBook #11 | whether the Hatter answers his riddle |
| Website | Python 3.13.14 documentation | recommended token randomness |
| Dataset | NASA GISTEMP v4 snapshot | the 2024 annual anomaly |
| Paper | FAIR Principles, PMCID PMC4792175 | the meaning of machine-actionable |

Each source is retained as an unmodified local snapshot. The
[`real-sources.json`](sources/real-sources.json) manifest records its publisher
URL, format, version, license, snapshot filename, and SHA-256. The build fails
if any byte no longer matches.

Every resource is committed in three layers:

1. `sources/` — publisher snapshots and their provenance manifest;
2. `packs/` — actual agent-native packs, generated CLIs, interface manifests,
   skills, and AGENT guides;
3. `results/` — exact evidence, CLI, MCP, and quality transcripts consumed by
   the HTML walkthrough.

## Rebuild and verify

From the repository root:

```bash
python demos/build_demos.py
python demos/verify_demos.py
```

Missing snapshots are downloaded from their declared publisher URL, then
verified. Existing snapshots are never silently refreshed. The builder removes
`OPENROUTER_API_KEY` and `AGENTIC_API_KEY` from child processes and normalizes
capture timestamps, so no credential, paid request, or model output is needed.

To view the page locally:

```bash
python -m http.server 8000 --directory demos
# open http://localhost:8000/
```

## Scope

The demo validates deterministic capture, focused evidence retrieval, generated
resource CLIs, stable interface manifests, and read-only MCP access over pinned
real resources. The short evidence-backed answers are editorially curated and
verified against the captured text; this is not a benchmark of generative answer
quality or human productivity.
