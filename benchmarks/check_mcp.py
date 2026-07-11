#!/usr/bin/env python3
"""Protocol and installed-host smoke checks for Agentic Anything MCP."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from agentic_anything.ingest import build_pack_from_source  # noqa: E402


def request(request_id, method, params=None):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def command(*args, env=None, timeout=30):
    proc = subprocess.run(args, text=True, capture_output=True, env=env, timeout=timeout)
    return {
        "args": list(args),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.work_dir.exists():
        shutil.rmtree(args.work_dir)
    args.work_dir.mkdir(parents=True)
    pack = args.work_dir / "handbook"
    build_pack_from_source(
        str(ROOT / "tests" / "fixtures" / "resources" / "handbook.md"),
        pack,
        site_id="handbook",
    )

    messages = [
        request(1, "initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "agentic-anything-check", "version": "1"},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        request(2, "ping"),
        request(3, "tools/list"),
        request(4, "tools/call", {
            "name": "search_resource", "arguments": {"query": "Team tier price", "top_k": 2}
        }),
        request(5, "resources/list"),
        request(6, "prompts/list"),
        request(7, "prompts/get", {
            "name": "use_resource", "arguments": {"question": "How much is Team?"}
        }),
        request(8, "tools/call", {"name": "missing", "arguments": {}}),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    proc = subprocess.run(
        [sys.executable, "-m", "agentic_anything", "mcp", str(pack)],
        input="".join(json.dumps(item) + "\n" for item in messages),
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )
    responses = [json.loads(line) for line in proc.stdout.splitlines()]
    by_id = {item["id"]: item for item in responses}
    assertions = {
        "server_exit_zero": proc.returncode == 0,
        "stderr_empty": proc.stderr == "",
        "notification_has_no_response": len(responses) == len(messages) - 1,
        "protocol_negotiated": by_id[1]["result"]["protocolVersion"] == "2025-11-25",
        "ping": by_id[2]["result"] == {},
        "tools": {tool["name"] for tool in by_id[3]["result"]["tools"]}
        == {"resource_info", "search_resource", "read_unit"},
        "search_has_hit": bool(by_id[4]["result"]["structuredContent"]["hits"]),
        "resources_listed": bool(by_id[5]["result"]["resources"]),
        "prompts_listed": bool(by_id[6]["result"]["prompts"]),
        "prompt_rendered": bool(by_id[7]["result"]["messages"]),
        "invalid_tool_structured": by_id[8]["result"]["isError"] is True,
    }

    codex = shutil.which("codex")
    claude = shutil.which("claude")
    hosts = {}
    if codex:
        codex_home = args.work_dir / "codex-home"
        codex_home.mkdir()
        codex_env = env | {"CODEX_HOME": str(codex_home)}
        hosts["codex_version"] = command(codex, "--version", env=codex_env)
        hosts["codex_add"] = command(
            codex, "mcp", "add", "--env", f"PYTHONPATH={SRC}", "agentic-anything", "--",
            sys.executable, "-m", "agentic_anything", "mcp", str(pack), env=codex_env,
        )
        hosts["codex_list"] = command(codex, "mcp", "list", env=codex_env)
        assertions["codex_config_accepted"] = (
            hosts["codex_add"]["returncode"] == 0
            and "enabled" in hosts["codex_list"]["stdout"]
        )
    if claude:
        claude_home = args.work_dir / "claude-home"
        claude_home.mkdir()
        claude_env = env | {"CLAUDE_CONFIG_DIR": str(claude_home)}
        hosts["claude_version"] = command(claude, "--version", env=claude_env)
        hosts["claude_add"] = command(
            claude, "mcp", "add", "--scope", "user", "--transport", "stdio",
            "agentic-anything", "-e", f"PYTHONPATH={SRC}", "--", sys.executable, "-m",
            "agentic_anything", "mcp", str(pack), env=claude_env,
        )
        hosts["claude_list"] = command(claude, "mcp", "list", env=claude_env, timeout=45)
        assertions["claude_connected"] = (
            hosts["claude_add"]["returncode"] == 0
            and "Connected" in hosts["claude_list"]["stdout"]
        )

    payload = {
        "experiment": "Agentic Anything MCP conformance and installed-host smoke test",
        "assertions": assertions,
        "passed": sum(assertions.values()),
        "total": len(assertions),
        "protocol_responses": responses,
        "hosts": hosts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": payload["passed"], "total": payload["total"]}))
    print(args.output)
    return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
