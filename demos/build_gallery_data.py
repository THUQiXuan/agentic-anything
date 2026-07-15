#!/usr/bin/env python3
"""Assemble demos/results/gallery-data.json for the demo gallery page.

Everything in the file is derived from committed artifacts — packs, recorded
runs, and recorded conversations. The gallery is a replay surface: this script
adds no new facts, it only reshapes existing ones for display.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
PACKS = DEMO / "packs"
RUNS = DEMO / "runs"
RESULTS = DEMO / "results"
SOURCES = DEMO / "sources"

COURSE_COMMAND = (
    "agentic-anything agentify https://cs336.stanford.edu/spring2025/ \\\n"
    "    --follow-docs 6 --follow-repos 1 -o packs/cs336-course"
)
FOOTAGE_COMMAND = (
    "agentic-anything agentify ./footage -o packs/footage-library"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def page_excerpt(pack: Path, page_id: str, limit: int = 620) -> dict:
    manifest = load(pack / "pages" / f"{page_id}.json")
    text_blocks = []
    for block in manifest.get("content", []):
        text = block.get("text", "").strip()
        if text:
            text_blocks.append(text)
        if sum(len(t) for t in text_blocks) > limit:
            break
    excerpt = "\n".join(text_blocks)[:limit]
    return {
        "page_id": page_id,
        "title": manifest.get("title", page_id),
        "locator": manifest.get("locator") or manifest.get("url_path") or "",
        "source_url": manifest.get("source_url", ""),
        "unit_kind": manifest.get("unit_kind", manifest.get("page_type", "")),
        "sha256": manifest.get("provenance", {}).get("content_sha256", ""),
        "excerpt": excerpt,
        "attachment_kind": manifest.get("provenance", {}).get("attachment_kind"),
    }


def conversations_for(pack_id: str, chats: dict, pack: Path,
                      order: list[str] | None = None) -> list[dict]:
    out = []
    for conversation in chats["conversations"]:
        if conversation["pack"] != pack_id:
            continue
        out.append({
            **{k: conversation[k] for k in ("id", "persona", "question", "answer")},
            "citations": [page_excerpt(pack, cid) for cid in conversation["citations"]],
        })
    if order:
        rank = {cid: i for i, cid in enumerate(order)}
        out.sort(key=lambda c: rank.get(c["id"], 99))
    return out


def run_summary(run_id: str) -> dict:
    run = load(RUNS / run_id / "run.json")
    verification = load(RUNS / run_id / "verification.json")
    steps = [
        {
            "step": s["step"],
            "phase": s["phase"],
            "tool": s["tool"],
            "input": s.get("tool_input", {}),
            "summary": s["output_summary"],
        }
        for s in run["steps"]
    ]
    return {
        "run_id": run_id,
        "task": run["task"],
        "mode": run["mode"],
        "model_calls": run.get("model_calls", 0),
        "summary": run["summary"],
        "steps": steps,
        "checks_passed": verification["assertions_passed"],
        "checks_total": verification["assertions_total"],
        "artifact_path": f"runs/{run_id}/artifact.md",
        "run_path": f"runs/{run_id}/run.json",
    }


def course_scenario(chats: dict) -> dict:
    pack = PACKS / "cs336-course"
    site = load(pack / "site.json")
    manifest = load(SOURCES / "real-sources.json")
    pinned = manifest["remote_pinned"]["cs336-course"]
    dead_links = [
        e for e in site["frontier"]
        if e["skip_reason"].startswith("attachment_fetch_failed")
    ]
    videos_or_more = sum(
        e["skip_reason"] in ("attachment_budget_exhausted", "attachment_not_followed")
        for e in site["frontier"]
    )
    return {
        "id": "course",
        "icon": "🎓",
        "label": "Open course",
        "tagline": "One course URL → a study-ready course agent",
        "before": {
            "title": "CS336 · Language Modeling from Scratch (Stanford, Spring 2025)",
            "url": site["seed_url"],
            "kind": "A schedule page for humans",
            "facts": [
                "1 HTML page links everything",
                "19 lecture PDFs live in a GitHub repo",
                "5 assignment starter repositories",
                "executable lecture traces + archives",
            ],
            "pain": "An agent given only the URL sees one page of links — the actual knowledge is scattered across hosts and formats.",
        },
        "command": COURSE_COMMAND,
        "build_events": [
            {
                "kind": att["kind"],
                "title": att["title"],
                "units": att["unit_count"],
                "bytes": att["content_bytes"],
                "sha256": att["content_sha256"][:12],
            }
            for att in site["attachments"]
        ],
        "after": {
            "crawled_pages": site["page_count"],
            "attachment_units": site["attachment_page_count"],
            "frontier": len(site["frontier"]),
            "dead_links_recorded": len(dead_links),
            "not_followed_recorded": videos_or_more,
            "capabilities": load(pack / "agent-pack.json")["capabilities"],
            "interfaces": sorted(load(pack / "agent-interface.json")["interfaces"].keys()),
        },
        "dead_link_example": dead_links[0] if dead_links else None,
        "conversations": conversations_for(
            "cs336-course", chats, pack,
            order=["course-slides", "course-handout", "course-implement"]),
        "run": run_summary("cs336-course-week1"),
        "source_note": pinned["note"],
    }


def footage_scenario(chats: dict) -> dict:
    pack = PACKS / "footage-library"
    site = load(pack / "site.json")
    manifest = load(SOURCES / "real-sources.json")["sources"]
    films = [
        manifest["footage-elephants-dream"],
        manifest["footage-sintel"],
        manifest["footage-tears-of-steel"],
    ]
    run = run_summary("footage-teaser-cut")
    result = load(RUNS / "footage-teaser-cut" / "run.json")["result"]
    return {
        "id": "footage",
        "icon": "🎬",
        "label": "Footage library",
        "tagline": "Raw clips + subtitles → a footage agent that cuts by quote",
        "before": {
            "title": "A creator's footage folder — three films, no script",
            "url": "demos/sources/footage/",
            "kind": "Folder of media transcripts",
            "facts": [
                "3 open films (Blender Foundation, CC-BY)",
                "subtitles only — no script, no notes",
                "answers live at exact millisecond offsets",
            ],
            "pain": "Finding 'the moment she says X' means scrubbing three timelines by hand.",
        },
        "command": FOOTAGE_COMMAND,
        "build_events": [
            {
                "kind": "transcript",
                "title": film["title"],
                "license": film["license"],
                "media_url": film["media_url"],
            }
            for film in films
        ],
        "after": {
            "crawled_pages": 0,
            "attachment_units": site["page_count"],
            "frontier": len(site["frontier"]),
            "unit_shape": "3-minute windows, every cue stamped [start → end]",
            "interfaces": sorted(load(pack / "agent-interface.json")["interfaces"].keys()),
        },
        "conversations": conversations_for("footage-library", chats, pack),
        "run": run,
        "edl": result["clips"],
        "edl_total_seconds": result["total_seconds"],
    }


def more_resources() -> list[dict]:
    showcase = load(RESULTS / "showcase.json")
    llm = load(RUNS / "requests-redirect-impact-llm" / "run.json")
    grid = []
    icons = {"requests": "📦", "alice": "📖", "secrets": "🐍",
             "gistemp": "📊", "fair-paper": "📄"}
    kinds = {"requests": "GitHub repository", "alice": "EPUB book",
             "secrets": "Docs website", "gistemp": "NASA dataset (CSV)",
             "fair-paper": "Scholarly article"}
    for item in showcase["demos"]:
        demo_id = item["id"]
        entry = {
            "id": demo_id,
            "icon": icons[demo_id],
            "kind": kinds[demo_id],
            "title": item["source"]["title"],
            "publisher": item["source"]["publisher"],
            "question": item["question"],
            "answer": item["answer"],
            "unit_count": item["unit_count"],
            "sha256": item["source"]["sha256"][:12],
            "license": item["source"]["license"],
            "evidence": {
                "unit": item["query_result"]["unit_id"],
                "locator": item["query_result"].get("locator", ""),
                "sha256": item["query_result"].get("content_sha256", "")[:12],
                "blocks": [
                    block["text"][:360]
                    for block in item["query_result"]["evidence_blocks"][:2]
                ],
            },
        }
        if demo_id == "requests":
            entry["llm_run"] = {
                "run_id": llm["run_id"],
                "model_calls": llm["recording"]["model_calls"],
                "steps": len(llm["steps"]),
                "note": "a real gpt-4.1-mini tool loop over stdio MCP, rejections preserved",
                "run_path": f"runs/{llm['run_id']}/run.json",
            }
        grid.append(entry)
    return grid


def main() -> int:
    chats = load(RUNS / "recorded-chats.json")
    runs_index = load(RUNS / "index.json")
    payload = {
        "schema_version": "1.0",
        "generated_from": "committed packs, recorded runs, recorded conversations",
        "chat_model": chats["model"],
        "chat_note": chats["note"],
        "scenarios": [course_scenario(chats), footage_scenario(chats)],
        "more": more_resources(),
        "totals": {
            "runs": runs_index["summary"]["run_count"],
            "run_checks_passed": runs_index["summary"]["assertions_passed"],
            "run_checks_total": runs_index["summary"]["assertions_total"],
            "recorded_model_calls": runs_index["model_calls"] + chats["model_calls"],
        },
    }
    out = RESULTS / "gallery-data.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    size = out.stat().st_size
    print(f"✓ gallery data: {out.relative_to(ROOT)} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
