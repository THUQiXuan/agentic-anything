# Agentic Anything long-horizon demo gallery

[Open the hosted gallery](https://thuqixuan.github.io/agentic-anything/) ·
[inspect the run index](runs/index.json) ·
[audit the source manifest](sources/real-sources.json) ·
[read the main project documentation](../README.md)

The gallery answers a harder question than “can the pack retrieve one fact?”:
can an agent use a pack across a long task, produce a useful file, and leave
enough evidence for another process to check the work?

## Three recorded runs

| Run | Controller | Horizon | Output | Checks |
|---|---|---:|---|---:|
| Requests redirect impact | Real `openai/gpt-4.1-mini` tool loop over stdio MCP + deterministic offline reviewer | 19 recorded model/MCP steps + 2 offline steps | raw accepted draft + reviewed maintainer brief + claim ledger | 9/9 |
| NASA GISTEMP + FAIR audit | Deterministic evidence agent over two packs | 16 steps | computed climate brief + 15-principle audit | 23/23 |
| Requests redirect impact | Deterministic evidence agent | 14 steps | reproducible change-impact report | 20/20 |

The real model run starts with no repository context. It makes 19 tool calls,
including five searches and eleven reads. Its first submission is rejected for
missing search/documentation coverage. Recorded model/MCP activity ends at step
19. Steps 20–21 are explicitly labeled deterministic offline review/publish
operations: they catch a subtler problem where the model attributed
`max_redirects` to a docs unit that never says it.

[`raw-transcript.json`](runs/requests-redirect-impact-llm/raw-transcript.json)
contains only the recorded model messages/tool calls and MCP exchanges behind
steps 1–19; it is not a transcript of the two offline steps. The reviewer
extracts the last accepted `submit_deliverable.artifact_markdown` verbatim into
[`accepted-model-draft.md`](runs/requests-redirect-impact-llm/accepted-model-draft.md),
then applies five named, exact-once replacements to regenerate the reviewed
artifact. A previously edited artifact is never a review input.

Every final LLM citation was read before publication, but not every read was
search-discovered. In particular, `quickstart.rst` did not occur in the prior
ranked search results: the first rejected submission's evidence gate explicitly
required that unit, after which the model read it directly. The run and verifier
label this path `evidence-gate-directed-read` instead of implying a universal
search→read→cite sequence.

The deterministic runs are not presented as LLM reasoning. They are explicit,
task-specific agent policies that drive fresh `agentic-anything mcp` subprocesses,
parse returned evidence, compute results, and reject citations to units that were
not searched and read first. They can be rebuilt byte-for-byte without a key.
In the FAIR table, runtime claims such as “searchable through this local MCP
run” use separate `RUN-*` references to exact run steps and raw exchanges;
GISTEMP/FAIR pack citations are not presented as proof of runtime behavior.

## What is checked in

```text
demos/
├── sources/                       # five byte-for-byte publisher snapshots
├── packs/                         # generated agent-native representations
├── runs/
│   ├── requests-redirect-impact-llm/
│   │   ├── run.json               # public step timeline and checked claims
│   │   ├── raw-transcript.json    # model messages + full MCP JSON-RPC
│   │   ├── accepted-model-draft.md # verbatim last accepted raw model draft
│   │   └── maintainer-impact-brief.md
│   ├── gistemp-fair-audit/        # run, artifact, raw events, verification
│   └── requests-redirect-impact/  # run, artifact, raw events, verification
├── build_demos.py                 # rebuild authentic packs (zero model calls)
├── build_agent_runs.py            # replay deterministic agents
├── record_llm_run.py              # optional paid one-time recorder
├── review_recorded_llm_run.py     # raw-draft extraction + deterministic review transform
└── verify_demos.py                # publishability and lineage checks
```

Every upstream resource still has a publisher URL, pinned version, license, and
snapshot SHA-256 in [`real-sources.json`](sources/real-sources.json). The pack
build verifies those bytes before doing any transformation.

## Rebuild and verify

From the repository root:

```bash
PYTHONPATH=src python demos/build_demos.py
PYTHONPATH=src python demos/review_recorded_llm_run.py
PYTHONPATH=src python demos/build_agent_runs.py
PYTHONPATH=src python demos/verify_demos.py
```

This rebuilds five packs, regenerates the accepted draft and reviewed artifact
from the raw recording, replays both deterministic runs through real stdio MCP
processes, and checks 52 long-run assertions. It makes no paid calls.

To record a fresh model trajectory instead:

```bash
export OPENROUTER_API_KEY="<your-key>"
PYTHONPATH=src python demos/record_llm_run.py --model openai/gpt-4.1-mini
PYTHONPATH=src python demos/review_recorded_llm_run.py
PYTHONPATH=src python demos/build_agent_runs.py
```

The key is read only from the process environment. It is never written to a
pack, transcript, artifact, or page.

To view the page locally:

```bash
python -m http.server 8000 --directory demos
# open http://localhost:8000/
```

## Scope

- “Replay” animates committed events; GitHub Pages does not run an agent server.
- The raw model/MCP transcript covers steps 1–19 only; steps 20–21 are
  deterministic offline review/publish records in `run.json`.
- The recorded model output is not accepted merely because it sounds plausible.
- Deterministic agents demonstrate long tool use and computation, not hidden
  model reasoning.
- MCP access is read-only, and no upstream resource is changed.
- Code units may be truncated at the pack capture limit; the complete release
  archive is authenticated separately by its snapshot hash.
