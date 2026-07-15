#!/usr/bin/env python3
"""Build the CS336 course-agent showcase pack from the live web.

This is the one demo pack whose sources are remote-pinned instead of being
committed: the upstream materials (lecture PDFs, the assignment repository)
are too large to vendor, so this script records their exact URLs, sizes, and
SHA-256 digests in ``demos/sources/real-sources.json`` after a build. CI does
NOT run this script; it verifies the committed pack's internal consistency
offline (``verify_demos.py``).

Usage:
    PYTHONPATH=src python demos/build_course_pack.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
SRC = ROOT / "src"
PACK = DEMO / "packs" / "cs336-course"
SOURCE_MANIFEST = DEMO / "sources" / "real-sources.json"

COURSE_URL = "https://cs336.stanford.edu/spring2025/"
SITE_ID = "cs336-course"
SNAPSHOT_AT = "2026-07-15T00:00:00Z"


def run(*args: str, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    env = {**__import__("os").environ, "PYTHONPATH": str(SRC)}
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("AGENTIC_API_KEY", None)
    proc = subprocess.run(list(args), cwd=ROOT, env=env, text=True,
                          capture_output=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def normalize_timestamps(pack: Path) -> None:
    site = json.loads((pack / "site.json").read_text(encoding="utf-8"))
    replacements = {}
    for field in ("captured_at", "finished_at"):
        if site.get(field):
            replacements[site[field]] = SNAPSHOT_AT
    for path in pack.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".md", ".py", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        for private, public in replacements.items():
            text = text.replace(private, public)
        path.write_text(text, encoding="utf-8")


def main() -> int:
    import shutil

    if PACK.exists():
        shutil.rmtree(PACK)

    print(f"building course pack from {COURSE_URL} (live network)…")
    run(
        sys.executable, "-m", "agentic_anything", "agentify", COURSE_URL,
        "-o", str(PACK), "--site-id", SITE_ID, "--no-llm", "--language", "both",
        "--max-pages", "8", "--follow-docs", "6", "--follow-repos", "1",
        "--json",
    )
    normalize_timestamps(PACK)

    site = json.loads((PACK / "site.json").read_text(encoding="utf-8"))
    attachments = site.get("attachments", [])
    failed = [
        entry for entry in site.get("frontier", [])
        if entry["skip_reason"].startswith("attachment_fetch_failed")
    ]

    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    manifest.pop("cs336-course", None)  # migrate any top-level legacy entry
    manifest.setdefault("remote_pinned", {})["cs336-course"] = {
        "title": "CS336: Language Modeling from Scratch (Spring 2025)",
        "publisher": "Stanford University",
        "resource_type": "course",
        "format": "live web capture with deep-captured attachments",
        "version": f"snapshot {SNAPSHOT_AT}",
        "origin_url": COURSE_URL,
        "snapshot": "remote-pinned",
        "note": (
            "Course page and lecture-viewer HTML are stored inside the pack "
            "(html/). Linked lecture PDFs and the assignment repository are "
            "not vendored; their exact download URLs, sizes, and SHA-256 "
            "digests are pinned below and inside every attachment page's "
            "provenance. Rebuild live with demos/build_course_pack.py."
        ),
        "license": "Course materials © Stanford CS336 staff; captured for a research/interoperability demo with links to the originals.",
        "license_url": "https://cs336.stanford.edu/spring2025/",
        "attachments": [
            {
                "title": att["title"],
                "kind": att["kind"],
                "url": att["url"],
                "fetched_url": att["fetched_url"],
                "sha256": att["content_sha256"],
                "bytes": att["content_bytes"],
            }
            for att in attachments
        ],
        "dead_links_recorded": [
            {"url": entry["url"], "skip_reason": entry["skip_reason"]}
            for entry in failed
        ],
    }
    SOURCE_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    print(f"✓ pack: {PACK.relative_to(ROOT)}")
    print(f"✓ pages: {site['page_count']} crawled + {site['attachment_page_count']} attachment units")
    print(f"✓ attachments: {len(attachments)} captured, {len(failed)} dead links recorded")
    print(f"✓ source manifest updated: {SOURCE_MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
