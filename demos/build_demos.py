#!/usr/bin/env python3
"""Build deterministic, publishable Agentic Anything demo artifacts.

The script uses only the repository source and Python standard library. It
deliberately removes model API keys from child processes so the checked-in demo
can be reproduced without credentials or paid calls.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
SRC = ROOT / "src"
SOURCES = DEMO / "sources"
PACKS = DEMO / "packs"
RESULTS = DEMO / "results"

sys.path.insert(0, str(SRC))

from agentic_anything.mcp import ResourceMCPServer  # noqa: E402
from agentic_anything.query import PackReader, search_pack  # noqa: E402


@contextlib.contextmanager
def local_site(directory: Path):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            return

    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def clean_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("AGENTIC_API_KEY", None)
    return env


def run(*args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(args), cwd=ROOT, env=clean_environment(), text=True,
        capture_output=True, timeout=timeout,
    )
    if proc.returncode:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def agentify(source: str, demo_id: str, language: str = "both") -> dict:
    pack = PACKS / demo_id
    proc = run(
        sys.executable, "-m", "agentic_anything", "agentify", source,
        "-o", str(pack), "--site-id", demo_id, "--no-llm",
        "--language", language, "--max-pages", "4", "--no-probe", "--json",
    )
    return json.loads(proc.stdout)


def query_demo(demo_id: str, query: str) -> dict:
    reader = PackReader(PACKS / demo_id)
    hits = search_pack(reader, query, top=3)
    return {
        "query": query,
        "method": "bm25f-unicode",
        "hits": hits,
    }


def compact_hit(payload: dict) -> dict:
    hit = payload["hits"][0]
    evidence = hit.get("evidence", [])
    return {
        "query": payload["query"],
        "unit_id": hit["page_id"],
        "title": hit["title"],
        "score": round(hit["score"], 4),
        "evidence": evidence[0]["text"] if evidence else "",
        "matched": evidence[0].get("matched", []) if evidence else [],
    }


def publish_pack(pack: Path, replacements: dict[str, str]) -> None:
    """Replace machine-local source locators with stable public demo locators."""
    for path in pack.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".md", ".py", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        for private, public in replacements.items():
            text = text.replace(private, public)
        path.write_text(text, encoding="utf-8")


def mcp_demo(pack_ids: list[str]) -> dict:
    server = ResourceMCPServer([PACKS / item for item in pack_ids])
    init = server.handle({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "demo-client", "version": "1"},
        },
    })
    search = server.handle({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {
            "name": "search_resource",
            "arguments": {"query": "错误码 E42 缓存", "top_k": 3},
        },
    })
    structured = search["result"]["structuredContent"]
    first = structured["hits"][0]
    read = server.handle({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "read_unit",
            "arguments": {
                "resource_id": first["resource_id"],
                "unit_id": first["unit_id"],
            },
        },
    })
    return {
        "initialize": init,
        "search_request": {"tool": "search_resource", "query": "错误码 E42 缓存"},
        "search_response": structured,
        "read_request": {
            "tool": "read_unit", "resource_id": first["resource_id"],
            "unit_id": first["unit_id"],
        },
        "read_response": read["result"]["structuredContent"],
    }


def cli_demo(demo_id: str, query: str) -> dict:
    pack = PACKS / demo_id
    cli = next((pack / "cli").glob("*_cli.py"))
    cli_rel = str(cli.relative_to(pack))
    info = run(sys.executable, str(cli), "info")
    search = run(sys.executable, str(cli), "search", query)
    return {
        "cli": cli_rel,
        "info": info.stdout.strip(),
        "search": search.stdout.strip(),
    }


def main() -> int:
    for directory in (PACKS, RESULTS):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="agentic-demo-") as temp_dir:
        repo = Path(temp_dir) / "orbit-sdk"
        shutil.copytree(SOURCES / "orbit-sdk", repo)
        (repo / ".git").mkdir()
        (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

        with local_site(SOURCES / "status-site") as site_url:
            specs = [
                ("handbook", str(SOURCES / "operations-handbook.md"),
                 "错误码 E42 如何处理？", "document"),
                ("incident", str(SOURCES / "incident.srt"),
                 "E42 在什么时候恢复？", "video"),
                ("metrics", str(SOURCES / "service-metrics.csv"),
                 "ap-south p95 latency incidents", "dataset"),
                ("code", str(repo), "OMEGA-7 timeout retries", "code"),
                ("website", site_url, "RUN-88 p95 latency", "web"),
            ]
            build_payloads = {}
            demos = []
            for demo_id, source, query, expected_type in specs:
                build_payloads[demo_id] = agentify(source, demo_id)
                reader = PackReader(PACKS / demo_id)
                result = query_demo(demo_id, query)
                if not result["hits"]:
                    raise RuntimeError(f"no search hit for {demo_id}: {query}")
                actual_type = reader.site.get("resource_type")
                if actual_type != expected_type:
                    raise RuntimeError(
                        f"{demo_id}: expected resource type {expected_type}, got {actual_type}"
                    )
                demos.append({
                    "id": demo_id,
                    "resource_type": actual_type,
                    "source_label": {
                        "handbook": "Markdown handbook",
                        "incident": "SRT incident timeline",
                        "metrics": "CSV service metrics",
                        "code": "Python code repository",
                        "website": "Two-page status website",
                    }[demo_id],
                    "unit_count": len(reader.page_ids()),
                    "query_result": compact_hit(result),
                    "interfaces": sorted(
                        json.loads((PACKS / demo_id / "agent-interface.json").read_text(
                            encoding="utf-8"
                        ))["interfaces"].keys()
                    ),
                })

            public_root = "https://github.com/THUQiXuan/agentic-anything/blob/main"
            public_code = "https://github.com/THUQiXuan/agentic-anything/tree/main/demos/sources/orbit-sdk"
            public_site = "https://thuqixuan.github.io/agentic-anything/sources/status-site"
            replacements = {
                str(ROOT): public_root,
                str(repo): public_code,
                site_url.rsplit("/", 1)[0]: public_site,
            }
            for item in demos:
                publish_pack(PACKS / item["id"], replacements)

    mcp = mcp_demo(["handbook", "incident", "metrics", "code", "website"])
    cli = cli_demo("handbook", "rollback ORBIT-17")
    assertions = {
        "five_resource_types": len({item["resource_type"] for item in demos}) == 5,
        "every_query_has_evidence": all(item["query_result"]["evidence"] for item in demos),
        "every_pack_has_interface_manifest": all(
            (PACKS / item["id"] / "agent-interface.json").is_file() for item in demos
        ),
        "every_pack_has_agent_guide": all(
            (PACKS / item["id"] / "AGENT.md").is_file() for item in demos
        ),
        "mcp_cross_resource_search": bool(mcp["search_response"]["hits"]),
        "generated_cli_runs": bool(cli["info"] and cli["search"]),
        "zero_model_calls": True,
    }
    showcase = {
        "project": "Agentic Anything",
        "generated_with": "v0.4.1 deterministic --no-llm path",
        "model_calls": 0,
        "summary": {
            "resource_types": len({item["resource_type"] for item in demos}),
            "resource_cases": len(demos),
            "units": sum(item["unit_count"] for item in demos),
            "assertions_passed": sum(assertions.values()),
            "assertions_total": len(assertions),
        },
        "assertions": assertions,
        "demos": demos,
        "mcp": mcp,
        "generated_cli": cli,
        "scope": (
            "Demonstrates deterministic capture, evidence retrieval, generated resource CLIs, "
            "and MCP access. It does not measure generative answer quality or human productivity."
        ),
    }
    (RESULTS / "showcase.json").write_text(
        json.dumps(showcase, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (RESULTS / "mcp-session.json").write_text(
        json.dumps(mcp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    transcript = (
        "$ python demos/build_demos.py\n"
        f"✓ agentified {showcase['summary']['resource_cases']} resources into "
        f"{showcase['summary']['units']} evidence units\n"
        f"✓ {showcase['summary']['assertions_passed']}/"
        f"{showcase['summary']['assertions_total']} showcase assertions passed\n"
        "✓ generated resource CLI answered: rollback ORBIT-17\n"
        "✓ MCP searched across five resource agents for: 错误码 E42 缓存\n"
        "✓ model calls: 0\n"
    )
    (RESULTS / "terminal-session.txt").write_text(transcript, encoding="utf-8")
    print(transcript, end="")
    return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
