#!/usr/bin/env python3
"""Validate the full resource -> pack -> resource-agent contract.

This is a deterministic system check, not an end-to-end answer-quality test.
It agentifies representative heterogeneous sources, verifies both discovery
contracts, exercises offline retrieval, and launches each generated resource
CLI.  No model or paid API is called.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from agentic_anything.query import PackReader, search_pack  # noqa: E402


@contextlib.contextmanager
def local_site(directory: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_agentify(source: str, pack: Path, resource_id: str) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("AGENTIC_API_KEY", None)
    proc = subprocess.run(
        [sys.executable, "-m", "agentic_anything", "agentify", source,
         "-o", str(pack), "--site-id", resource_id, "--no-llm", "--json"],
        text=True,
        capture_output=True,
        env=env,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"agentify failed for {resource_id}: {proc.stderr}\n{proc.stdout}")
    return json.loads(proc.stdout)


def validate_case(case_id: str, pack: Path, query: str, cli_path: str) -> dict:
    reader = PackReader(pack)
    manifest_path = pack / "agent-interface.json"
    guide_path = pack / "AGENT.md"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    discovery = reader.discovery
    required_interfaces = {"inspect", "search", "conversation", "mcp", "http_agent", "skill"}
    assertions = {
        "pack_discovery": discovery.get("kind") == "agentic-anything-pack",
        "resource_type_present": bool(reader.site.get("resource_type")),
        "agent_identity": (
            manifest.get("project") == "Agentic Anything"
            and manifest.get("kind") == "agentic-anything-resource-agent"
        ),
        "interface_discoverable": required_interfaces <= set(manifest.get("interfaces", {})),
        "representation_linked": (
            discovery.get("contents", {}).get("agent_interface") == "agent-interface.json"
            and "resource_agent_interface" in discovery.get("capabilities", [])
        ),
        "portable_interface_paths": (
            manifest.get("agent_native_representation", {}).get("root") == "."
            and manifest.get("agent_native_representation", {}).get("path_resolution")
            == "relative_to_agent-interface.json"
        ),
        "guide_present": guide_path.is_file() and "Resource Agent" in guide_path.read_text(encoding="utf-8"),
        "skill_present": (pack / "skills" / "SKILL.md").is_file(),
        "credentials_absent": "sk-or-" not in manifest_text and "API_KEY=" not in manifest_text,
        "offline_query_hit": bool(search_pack(reader, query, top=1)),
    }
    cli_proc = subprocess.run(
        [sys.executable, cli_path, "info"], text=True, capture_output=True, timeout=30
    )
    assertions["resource_cli_runs"] = cli_proc.returncode == 0
    return {
        "case": case_id,
        "resource_type": reader.site.get("resource_type"),
        "unit_count": len(reader.page_ids()),
        "query": query,
        "assertions": assertions,
        "passed": all(assertions.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True,
                        help="a real PDF used to exercise the PDF adapter")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.work_dir.exists():
        shutil.rmtree(args.work_dir)
    args.work_dir.mkdir(parents=True)
    sources = args.work_dir / "sources"
    packs = args.work_dir / "packs"
    sources.mkdir()
    packs.mkdir()

    site = sources / "site"
    site.mkdir()
    (site / "index.html").write_text(
        "<html><head><title>Launch Manual</title></head><body>"
        "<h1>Website resource</h1><p>The launch token is ZEPHYR-41.</p></body></html>",
        encoding="utf-8",
    )
    markdown = sources / "policy.md"
    markdown.write_text("# Refund policy\n\nThe refund window is 37 days.\n", encoding="utf-8")
    subtitle = sources / "incident.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:04,000\n错误码 E42 表示缓存锁定。\n",
        encoding="utf-8",
    )
    table = sources / "metrics.csv"
    table.write_text("region,score\nnorth,73\nsouth,58\n", encoding="utf-8")
    code = sources / "repository"
    code.mkdir()
    (code / ".git").mkdir()
    (code / "README.md").write_text("# Orbit SDK\nUse OMEGA-7 for retry mode.\n", encoding="utf-8")
    (code / "client.py").write_text("RETRY_MODE = 'OMEGA-7'\n", encoding="utf-8")

    case_specs: list[tuple[str, str, str]] = [
        ("document", str(markdown), "refund window 37 days"),
        ("video_transcript", str(subtitle), "错误码 E42"),
        ("tabular_data", str(table), "north 73"),
        ("code_repository", str(code), "OMEGA-7 retry mode"),
        ("pdf", str(args.pdf.resolve()), "Agentic Anything"),
        ("installed_software", "cli:python", "version information"),
    ]
    results: list[dict] = []
    with local_site(site) as url:
        case_specs.insert(0, ("website", url, "launch token ZEPHYR-41"))
        for case_id, source, query in case_specs:
            pack = packs / case_id
            payload = run_agentify(source, pack, case_id)
            results.append(validate_case(
                case_id, pack, query, payload["cli"]["cli_path"]
            ))

    all_assertions = [value for result in results for value in result["assertions"].values()]
    payload = {
        "experiment": "Agentic Anything heterogeneous resource-to-agent contract",
        "scope": "deterministic system validation; not generative answer quality",
        "model_calls": 0,
        "cases": results,
        "summary": {
            "resource_cases": len(results),
            "successful_agentifications": sum(result["passed"] for result in results),
            "assertions_passed": sum(all_assertions),
            "assertions_total": len(all_assertions),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(args.output)
    return 0 if all(all_assertions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
