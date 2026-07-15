# Agentic Anything demo gallery

[**Open the hosted gallery**](https://thuqixuan.github.io/agentic-anything/) ·
[run index](runs/index.json) ·
[source manifest](sources/real-sources.json) ·
[main documentation](../README.md)

The gallery answers three questions in one screen, per resource:
**what the resource was**, **what one command turned it into**, and
**what talking to it looks like** — with every reply being a *recorded,
offline-verifiable* replay, never a mockup.

## The two flagship scenarios

### 🎓 One course URL → a course agent (`packs/cs336-course`)

```bash
agentic-anything agentify https://cs336.stanford.edu/spring2025/ \
    --follow-docs 6 --follow-repos 1
```

Deep capture pulls six lecture PDF decks (page-addressable units) and the
`assignment1-basics` starter repository into the same pack, and records four
dead assignment-handout links in the frontier instead of hiding them. On top
of that pack we ship:

- **Three recorded real-model conversations** (`runs/recorded-chats.json`,
  `google/gemini-3.5-flash` over the production `chat --ask` path): which
  slide pages cover RoPE; where to start Assignment 1; and how to get the
  handout whose course-page link 404s — the agent routes around the dead link
  using the frontier record plus the repo tree, which lists
  `cs336_assignment1_basics.pdf (965,629 bytes)` beyond the text-capture
  boundary.
- **A 14-step deterministic run** (`runs/cs336-course-week1/`) through a real
  stdio MCP subprocess: 5 searches, 5 hash-verified reads, a link-rot check,
  and a cited week-1 study plan. 10/10 offline checks.

The pack's upstream materials are **remote-pinned**: exact URLs, sizes, and
SHA-256 digests live in `sources/real-sources.json → remote_pinned` and in
every attachment unit's provenance. Rebuild live with
`python demos/build_course_pack.py` (network required; CI never does this —
it verifies the committed pack offline instead).

### 🎬 A footage folder → a cutting agent (`packs/footage-library`)

```bash
agentic-anything agentify ./footage -o packs/footage-library
```

Three CC-BY Blender open-movie transcripts (Sintel, Tears of Steel, Elephants
Dream — byte-pinned in `sources/footage/`) become one searchable library whose
units stamp every cue: `[00:07:37.800 → 00:07:40.500] These are dragon lands,
Sintel.` On top:

- **Two recorded real-model conversations**: find every dragon mention with
  cuttable timecodes; pin the closing line's exact timing.
- **A 14-step deterministic run** (`runs/footage-teaser-cut/`) that assembles
  a themed teaser: every cut is pure ±0.75 s arithmetic on a cue that was
  read through MCP, the artifact carries per-film CC-BY attribution and
  executable ffmpeg commands against the official releases. 12/12 checks.

## Also in the gallery

- Five more resource shapes (Requests repo, *Alice in Wonderland* EPUB,
  docs.python.org, NASA GISTEMP CSV, the FAIR paper) with cited answers and
  pinned sources — plus the previously recorded **21-step real
  `openai/gpt-4.1-mini` tool loop** over stdio MCP
  (`runs/requests-redirect-impact-llm/`, evidence-gate rejections preserved)
  and two deterministic long runs (`requests-redirect-impact`,
  `gistemp-fair-audit`).
- In total: **5 runs, 74/74 offline checks**, and 15 recorded model calls
  (10 tool-loop + 5 chat) — all committed, none re-run in your browser.

## What is checked in

```text
demos/
├── index.html                 # the gallery (replay UI; fetches committed data only)
├── results/gallery-data.json  # display data derived from packs + runs + chats
├── sources/                   # byte-pinned snapshots + remote-pinned manifest
│   └── footage/               # three official film transcripts (CC-BY)
├── packs/                     # 7 committed packs (5 rebuilt in CI + course + footage)
├── runs/
│   ├── cs336-course-week1/         # run.json · artifact.md · verification · raw events
│   ├── footage-teaser-cut/
│   ├── requests-redirect-impact-llm/   # recorded model run (see below)
│   ├── requests-redirect-impact/
│   ├── gistemp-fair-audit/
│   ├── recorded-chats.json         # five real grounded conversations
│   └── index.json
├── build_demos.py             # rebuild the 5 showcase packs + footage (offline)
├── build_course_pack.py       # live rebuild of the course pack (network)
├── build_agent_runs.py        # replay the 4 deterministic runs over real MCP
├── build_gallery_data.py      # regenerate gallery-data.json
├── record_showcase_chats.py   # re-record the 5 conversations (needs a key)
├── record_llm_run.py          # re-record the model tool loop (needs a key)
├── review_recorded_llm_run.py # deterministic review of the recorded loop
├── render_hero_svg.py         # regenerate the README's animated SVG
└── verify_demos.py            # the offline gate CI runs
```

## Rebuild and verify (offline, what CI runs)

```bash
PYTHONPATH=src python demos/build_demos.py
PYTHONPATH=src python demos/review_recorded_llm_run.py
PYTHONPATH=src python demos/build_agent_runs.py
PYTHONPATH=src python demos/build_gallery_data.py
PYTHONPATH=src python demos/verify_demos.py
```

This makes **zero model calls** and is byte-deterministic: CI diffs
`demos/packs`, `demos/results`, and `demos/runs` against the committed tree.
`verify_demos.py` additionally re-hashes every course attachment unit,
re-checks that every recorded chat citation resolves to a real pack unit, and
re-validates all 74 run assertions.

To re-record the paid pieces instead (small, optional):

```bash
export OPENROUTER_API_KEY="<your-key>"
PYTHONPATH=src python demos/record_showcase_chats.py     # 5 chat completions
PYTHONPATH=src python demos/record_llm_run.py --model openai/gpt-4.1-mini
PYTHONPATH=src python demos/review_recorded_llm_run.py
```

The key is read only from the environment and never written to any artifact.

To view the gallery locally:

```bash
python -m http.server 8000 --directory demos
# open http://localhost:8000/
```

## Scope and honesty rules

- The page is a replay. GitHub Pages serves committed recordings; no model
  runs in the browser and no network calls leave the page except loading the
  committed JSON.
- Deterministic runs are explicit scripted policies over real MCP
  subprocesses — long tool use and computation, not hidden model reasoning.
  The two recorded-model surfaces (tool loop, chats) are labeled as such.
- Citations must exist: a run refuses to cite what it did not read, the chat
  recorder marks whether every citation resolved, and CI fails if any
  committed citation stops resolving.
- MCP access is read-only; no upstream resource is modified. Course materials
  remain © their authors; the Blender films are CC-BY with attribution
  carried into every artifact.
