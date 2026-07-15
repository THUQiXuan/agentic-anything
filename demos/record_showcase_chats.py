#!/usr/bin/env python3
"""Record a handful of REAL grounded conversations with resource agents.

This intentionally uses the production ``chat --ask`` path (retrieval +
OpenAI-compatible chat completion) against the committed packs, so the
gallery can replay authentic conversations instead of mockups.

- Requires OPENROUTER_API_KEY (or AGENTIC_API_KEY) in the environment.
- Makes one model call per question (five total by default).
- Writes demos/results/recorded-chats.json. The API key is never persisted.
- Offline verification: every citation must resolve to a page id inside the
  pack that produced it (checked here and again in verify_demos.py).

Usage:
    export OPENROUTER_API_KEY=...
    PYTHONPATH=src python demos/record_showcase_chats.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
SRC = ROOT / "src"
PACKS = DEMO / "packs"
OUT = DEMO / "runs" / "recorded-chats.json"
SNAPSHOT_AT = "2026-07-15T00:00:00Z"

QUESTIONS = [
    {
        "id": "course-implement",
        "pack": "cs336-course",
        "persona": "student",
        "question": (
            "I'm starting Assignment 1 this week. What exactly do I need to "
            "implement, and where do I start in the starter code?"
        ),
    },
    {
        "id": "course-slides",
        "pack": "cs336-course",
        "persona": "student",
        "question": (
            "Which lecture slides cover RoPE, and which pages should I read "
            "before implementing positional embeddings?"
        ),
    },
    {
        "id": "course-handout",
        "pack": "cs336-course",
        "persona": "student",
        "question": (
            "The Assignment 1 handout link on the course page 404s for me. "
            "Where can I actually get the handout?"
        ),
    },
    {
        "id": "footage-dragon",
        "pack": "footage-library",
        "persona": "creator",
        "question": (
            "Find the exact moments where anyone talks about a dragon. "
            "Give me timecodes I can cut."
        ),
    },
    {
        "id": "footage-closer",
        "pack": "footage-library",
        "persona": "creator",
        "question": (
            "For the closing shot I want the moment where Thom admits the "
            "world has changed. Find its exact timing."
        ),
    },
]


def ask(pack_dir: Path, question: str, model: str) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    proc = subprocess.run(
        [sys.executable, "-m", "agentic_anything", "chat", str(pack_dir),
         "--ask", question, "--model", model, "--json"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=240,
    )
    if proc.returncode:
        raise RuntimeError(f"chat failed: {proc.stderr[:2000]}")
    return json.loads(proc.stdout)


def main() -> int:
    if not (os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AGENTIC_API_KEY")):
        raise SystemExit("Set OPENROUTER_API_KEY to record real conversations")
    model = os.environ.get("AGENTIC_MODEL", "google/gemini-3.5-flash")

    conversations = []
    for spec in QUESTIONS:
        pack_dir = PACKS / spec["pack"]
        site = json.loads((pack_dir / "site.json").read_text(encoding="utf-8"))
        valid_ids = {page["page_id"] for page in site["pages"]}
        print(f"→ [{spec['pack']}] {spec['question'][:72]}…", file=sys.stderr)
        reply = ask(pack_dir, spec["question"], model)
        citations = reply.get("citations", [])
        resolved = [cid for cid in citations if cid in valid_ids]
        conversations.append({
            **{k: spec[k] for k in ("id", "pack", "persona", "question")},
            "answer": reply.get("answer", ""),
            "citations": citations,
            "citations_resolved_in_pack": resolved,
            "all_citations_resolve": bool(citations) and len(resolved) == len(citations),
            "used_units": reply.get("used_units", []),
        })

    payload = {
        "schema_version": "1.0",
        "recorded_at": SNAPSHOT_AT,
        "mode": "real-model-grounded-chat",
        "model": model,
        "provider_base": "openrouter (OpenAI-compatible)",
        "model_calls": len(conversations),
        "note": (
            "Authentic recorded replies from `agentic-anything chat --ask` over "
            "the committed packs. Citations are unit ids; verify_demos.py "
            "re-checks offline that each one resolves inside its pack."
        ),
        "conversations": conversations,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    ok = sum(c["all_citations_resolve"] for c in conversations)
    print(f"✓ recorded {len(conversations)} conversations with {model}")
    print(f"✓ {ok}/{len(conversations)} replies have fully resolving citations")
    print(f"✓ output: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
