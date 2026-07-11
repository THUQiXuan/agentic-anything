#!/usr/bin/env python3
"""Verify that the checked-in authentic-source demo is runnable and publish-safe."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
SOURCES = DEMO / "sources"
EXPECTED = {"requests", "alice", "secrets", "gistemp", "fair-paper"}
EXPECTED_PHRASES = {
    "requests": "DEFAULT_REDIRECT_LIMIT",
    "alice": "slightest idea",
    "secrets": "32 bytes (256 bits)",
    "gistemp": "2024 | 1.25",
    "fair-paper": "identify the type of object",
}
FORBIDDEN = ("/newcpfs/", "/tmp/", "sk-or-")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"✓ {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    source_manifest = json.loads((SOURCES / "real-sources.json").read_text(encoding="utf-8"))
    declared = source_manifest["sources"]
    check(set(declared) == EXPECTED, "source manifest declares exactly five real resources")
    for demo_id, meta in declared.items():
        source = SOURCES / meta["snapshot_file"]
        check(source.is_file(), f"{demo_id} source snapshot is checked in")
        check(sha256_file(source) == meta["sha256"], f"{demo_id} source SHA-256 matches publisher snapshot")
        check(meta["origin_url"].startswith("https://") and meta["license_url"].startswith("https://"),
              f"{demo_id} has public origin and license links")

    payload = json.loads((DEMO / "results" / "showcase.json").read_text(encoding="utf-8"))
    demos = {item["id"]: item for item in payload["demos"]}
    check(set(demos) == EXPECTED, "all five authentic demo resources are present")
    check(payload["summary"]["publishers"] == 5, "showcase spans five named publishers")
    check(payload["summary"]["resource_types"] == 5, "showcase spans five native resource types")
    check(payload["summary"]["units"] == 93, "showcase contains ninety-three real evidence units")
    check(payload["synthetic_source_lines"] == 0, "showcase declares zero synthetic source lines")
    check(len(payload["flagship"]["steps"]) == 3, "flagship traces definition, default, and enforcement")
    check(all(step["result"]["locator"] and step["result"]["content_sha256"]
              for step in payload["flagship"]["steps"]),
          "each flagship finding has an exact locator and content hash")
    check(all(payload["assertions"].values()), "all generated showcase quality assertions pass")
    check(payload["model_calls"] == 0, "demo build uses zero model calls")

    for demo_id, item in demos.items():
        evidence = " ".join(block["text"] for block in item["query_result"]["evidence_blocks"])
        check(EXPECTED_PHRASES[demo_id].casefold() in evidence.casefold(),
              f"{demo_id} checked answer is supported by visible evidence")
        check(item["source"]["sha256"] == declared[demo_id]["sha256"] and item["source"]["verified"],
              f"{demo_id} result retains source provenance")
        pack = DEMO / "packs" / demo_id
        site = json.loads((pack / "site.json").read_text(encoding="utf-8"))
        check("127.0.0.1:" not in site.get("seed_url", ""),
              f"{demo_id} public pack locator is not the local capture server")
        for relative in ("agent-pack.json", "agent-interface.json", "AGENT.md", "skills/SKILL.md"):
            check((pack / relative).is_file(), f"{demo_id} contains {relative}")
        cli = next((pack / "cli").glob("*_cli.py"))
        proc = subprocess.run(
            [sys.executable, str(cli), "info"], text=True, capture_output=True, timeout=30
        )
        check(proc.returncode == 0 and f"site_id: {demo_id}" in proc.stdout,
              f"{demo_id} generated CLI runs")

    publishable = [
        path for path in DEMO.rglob("*")
        if path.is_file() and path.suffix in {".json", ".md", ".py", ".html", ".txt"}
    ]
    leaks: list[str] = []
    for path in publishable:
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN:
            if path.name in {"verify_demos.py", "build_demos.py"}:
                continue
            if marker in text:
                leaks.append(f"{path.relative_to(ROOT)} contains {marker!r}")
    check(not leaks, "published artifacts exclude local paths and credential-shaped markers")

    html = (DEMO / "index.html").read_text(encoding="utf-8")
    required_story = (
        "results/showcase.json",
        "Before · authentic source",
        "After · agent-native pack",
        "Now use the transformed resource",
        "Every input has",
        "zero synthetic source lines",
        "Boundary of this demo",
    )
    check(all(marker in html for marker in required_story),
          "HTML leads with authenticity, before/after/use, and explicit limits")
    print("\nAuthentic-source demo verification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
