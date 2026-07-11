#!/usr/bin/env python3
"""Verify that the checked-in demo is complete, runnable, and publish-safe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
EXPECTED = {"handbook", "incident", "metrics", "code", "website"}
FORBIDDEN = ("/newcpfs/", "/tmp/agentic-demo", "127.0.0.1:", "sk-or-")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"✓ {message}")


def main() -> int:
    result_path = DEMO / "results" / "showcase.json"
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    ids = {item["id"] for item in payload["demos"]}
    check(ids == EXPECTED, "all five demo resources are present")
    check(all(payload["assertions"].values()), "all generated showcase assertions pass")
    check(payload["model_calls"] == 0, "demo uses zero model calls")

    for demo_id in sorted(EXPECTED):
        pack = DEMO / "packs" / demo_id
        for relative in ("agent-pack.json", "agent-interface.json", "AGENT.md", "skills/SKILL.md"):
            check((pack / relative).is_file(), f"{demo_id} contains {relative}")
        cli = next((pack / "cli").glob("*_cli.py"))
        proc = subprocess.run(
            [sys.executable, str(cli), "info"], text=True, capture_output=True, timeout=30
        )
        check(proc.returncode == 0 and f"site_id: {demo_id}" in proc.stdout,
              f"{demo_id} generated CLI runs")

    publishable = [path for path in DEMO.rglob("*") if path.is_file() and path.suffix in {".json", ".md", ".py", ".html", ".txt"}]
    leaks: list[str] = []
    for path in publishable:
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN:
            if path.name == "verify_demos.py":
                continue
            if path.name == "build_demos.py" and marker in {"/tmp/agentic-demo", "127.0.0.1:"}:
                continue
            if marker in text:
                leaks.append(f"{path.relative_to(ROOT)} contains {marker!r}")
    check(not leaks, "published artifacts exclude local paths and credential-shaped markers")

    html = (DEMO / "index.html").read_text(encoding="utf-8")
    check("results/showcase.json" in html and "Honest quality boundary" in html,
          "HTML gallery loads raw evidence and states its limits")
    print("\nDemo verification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
