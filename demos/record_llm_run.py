#!/usr/bin/env python3
"""Record one real LLM tool-use run against an Agentic Anything MCP server.

This is intentionally separate from ``build_demos.py``.  A recording may make
paid model calls once; the checked-in result is then verified and replayed
offline without an API key.  Credentials are read from the environment and are
never included in requests saved to disk.

The current task asks a model to produce a maintainer impact brief for changing
Requests' default redirect ceiling.  The model has no repository context in its
prompt: it must inspect, search, and read the pinned Requests pack through the
real stdio MCP process before ``submit_deliverable`` will accept its work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
PACK = DEMO / "packs" / "requests"
RUN_DIR = DEMO / "runs" / "requests-redirect-impact-llm"
SOURCE_MANIFEST = DEMO / "sources" / "real-sources.json"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_value(value: Any) -> Any:
    """Remove the checkout-specific prefix from publishable recordings."""
    if isinstance(value, str):
        return value.replace(str(ROOT), ".")
    if isinstance(value, list):
        return [portable_value(item) for item in value]
    if isinstance(value, dict):
        return {key: portable_value(item) for key, item in value.items()}
    return value


def clean_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    # The MCP server itself never needs or receives a model credential.
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("AGENTIC_API_KEY", None)
    return env


class MCPProcess:
    """Small newline-delimited JSON-RPC client for the real stdio server."""

    def __init__(self, pack: Path) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "agentic_anything", "mcp", str(pack)],
            cwd=ROOT,
            env=clean_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.next_id = 1
        self.raw_events: list[dict] = []

    def call(self, method: str, params: dict | None = None) -> dict:
        request_id = self.next_id
        self.next_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        started = time.monotonic()
        self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        duration_ms = round((time.monotonic() - started) * 1000)
        if not line:
            stderr = ""
            if self.process.stderr is not None:
                stderr = self.process.stderr.read()
            raise RuntimeError(f"MCP process ended without a response: {stderr[:1000]}")
        response = portable_value(json.loads(line))
        self.raw_events.append({
            "request": request,
            "response": response,
            "duration_ms": duration_ms,
        })
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        return response["result"]

    def close(self) -> None:
        if self.process.stdin is not None:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)


def model_request(
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict],
    tools: list[dict],
    timeout: float,
    require_tool: bool = False,
) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "required" if require_tool else "auto",
        "temperature": 0,
        "max_tokens": 5000,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=canonical_bytes(payload),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/THUQiXuan/agentic-anything",
            "X-Title": "Agentic Anything long-horizon demo recorder",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(2000).decode("utf-8", errors="replace")
        raise RuntimeError(f"model request failed (HTTP {exc.code}): {detail}") from exc
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"model returned no choices: {json.dumps(data)[:800]}")
    return data


def tool_payload(result: dict) -> dict:
    if result.get("isError"):
        return {"error": result.get("content", [{}])[0].get("text", "tool error")}
    return result.get("structuredContent") or {}


def compact_for_model(name: str, payload: dict, limit: int = 9000) -> dict:
    """Keep exact metadata and focused excerpts while bounding model context.

    The unabridged MCP payload remains in ``raw-transcript.json``.  The model
    receives windows around task-relevant symbols instead of an arbitrary file
    prefix; this mirrors how an agent host manages context without changing the
    evidence returned by the MCP server.
    """
    if name != "read_unit" or "markdown" not in payload:
        return payload
    value = dict(payload)
    markdown = str(value.pop("markdown"))
    needles = (
        "DEFAULT_REDIRECT_LIMIT",
        "max_redirects",
        "TooManyRedirects",
        "test_HTTP_302_TOO_MANY_REDIRECTS",
        "maximum redirections",
        "class RequestException",
    )
    windows: list[tuple[int, int]] = []
    folded = markdown.casefold()
    for needle in needles:
        start = 0
        while True:
            index = folded.find(needle.casefold(), start)
            if index < 0:
                break
            windows.append((max(0, index - 700), min(len(markdown), index + 1300)))
            start = index + len(needle)
    windows.sort()
    merged: list[tuple[int, int]] = []
    for start, end in windows:
        if merged and start <= merged[-1][1] + 120:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    excerpt = "\n\n[… focused evidence window …]\n\n".join(
        markdown[start:end] for start, end in merged
    )
    if not excerpt:
        excerpt = markdown[:limit]
    value["markdown_excerpt"] = excerpt[:limit]
    value["markdown_total_chars"] = len(markdown)
    value["markdown_truncated_for_model"] = len(markdown) > limit
    return value


def call_summary(name: str, arguments: dict, payload: dict) -> tuple[str, str, list[str]]:
    if name == "resource_info":
        return (
            "Inspect the captured repository",
            f"{payload.get('resource_type', 'resource')} pack; "
            f"{payload.get('page_count', len(payload.get('unit_ids', [])))} units; "
            f"{len(payload.get('frontier', []))} frontier entries.",
            [],
        )
    if name == "search_resource":
        hits = payload.get("hits", [])
        top = hits[0] if hits else {}
        return (
            f"Search · {arguments.get('query', '')}",
            (
                f"{len(hits)} ranked hits; top result is "
                f"{top.get('unit_id', 'none')} with query coverage "
                f"{top.get('query_coverage', 0)}."
            ),
            [item.get("unit_id", "") for item in hits if item.get("unit_id")],
        )
    if name == "read_unit":
        return (
            f"Read · {arguments.get('unit_id', '')}",
            f"Read {payload.get('locator', '')}; captured unit hash "
            f"{str(payload.get('content_sha256') or '')[:12]}…",
            [payload.get("unit_id", "")],
        )
    return (name, "Tool completed.", [])


def validate_submission(
    submission: dict,
    *,
    searches: list[dict],
    reads: dict[str, dict],
) -> tuple[list[dict], list[str]]:
    required_units = {
        "file__src--requests--models-py": "constant definition",
        "file__src--requests--sessions-py": "Session default and runtime guard",
        "file__src--requests--exceptions-py": "exception type",
        "file__tests--test-requests-py": "default/custom behavior tests",
        "file__docs--user--quickstart-rst": "documented public behavior",
    }
    errors: list[str] = []
    if len(searches) < 4:
        errors.append(f"use at least 4 focused searches (currently {len(searches)})")
    missing = [f"{unit} ({purpose})" for unit, purpose in required_units.items() if unit not in reads]
    if missing:
        errors.append("read these required evidence units: " + "; ".join(missing))
    artifact = str(submission.get("artifact_markdown") or "")
    for phrase in (
        "DEFAULT_REDIRECT_LIMIT",
        "max_redirects",
        "TooManyRedirects",
        "test_HTTP_302_TOO_MANY_REDIRECTS",
        "30",
    ):
        if phrase not in artifact:
            errors.append(f"artifact is missing required evidence term {phrase!r}")
    if "advanced.rst" in artifact:
        errors.append(
            "do not cite docs/user/advanced.rst: the captured unit does not document "
            "max_redirects; use quickstart.rst only for the documented exception behavior"
        )
    claims = submission.get("claims") or []
    if len(claims) < 5:
        errors.append("provide at least 5 separately cited claims")
    enriched: list[dict] = []
    supported_units: set[str] = set()
    claims_by_unit: dict[str, list[str]] = {}
    for index, claim in enumerate(claims, 1):
        unit_id = claim.get("unit_id")
        resource_id = claim.get("resource_id")
        if resource_id != "requests" or unit_id not in reads:
            errors.append(
                f"claim {index} must cite a requests unit that was read; got "
                f"{resource_id}/{unit_id}"
            )
            continue
        evidence = reads[unit_id]
        claim_text = str(claim.get("claim") or "").strip()
        supported_units.add(unit_id)
        claims_by_unit.setdefault(unit_id, []).append(claim_text)
        enriched.append({
            "claim_id": f"claim-{index:02d}",
            "text": claim_text,
            "support": {
                "resource_id": resource_id,
                "unit_id": unit_id,
                "locator": evidence.get("locator", ""),
                "captured_unit_sha256": evidence.get("content_sha256", ""),
                "uri": evidence.get("uri", ""),
            },
        })
    if not set(required_units).issubset(supported_units):
        errors.append("claim matrix must cover all five required evidence units")
    return enriched, errors


def submit_tool_schema() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "submit_deliverable",
            "description": (
                "Submit the final maintainer brief and claim-evidence matrix. "
                "The verifier rejects it until the required pack evidence has been read."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "artifact_markdown": {"type": "string"},
                    "claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim": {"type": "string"},
                                "resource_id": {"type": "string"},
                                "unit_id": {"type": "string"},
                            },
                            "required": ["claim", "resource_id", "unit_id"],
                            "additionalProperties": False,
                        },
                    },
                    "limitations": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "summary", "artifact_markdown", "claims", "limitations"],
                "additionalProperties": False,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("AGENTIC_MODEL", "openai/gpt-4.1-mini"))
    parser.add_argument("--base-url", default=os.environ.get("AGENTIC_BASE_URL", "https://openrouter.ai/api/v1"))
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-rounds", type=int, default=18)
    args = parser.parse_args()
    api_key = os.environ.get("AGENTIC_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Set AGENTIC_API_KEY or OPENROUTER_API_KEY to record a model run")
    if not PACK.is_dir():
        raise SystemExit("Build demos/packs first with: python demos/build_demos.py")

    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    source = source_manifest["sources"]["requests"]
    started_wall = datetime.now(timezone.utc)
    started = time.monotonic()
    server = MCPProcess(PACK)
    model_responses: list[dict] = []
    steps: list[dict] = []
    searches: list[dict] = []
    reads: dict[str, dict] = {}
    submission: dict | None = None
    enriched_claims: list[dict] = []
    try:
        initialized = server.call("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "long-horizon-demo-recorder", "version": "1"},
        })
        listed = server.call("tools/list")
        mcp_tools = [
            {
                "type": "function",
                "function": {
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "parameters": item["inputSchema"],
                },
            }
            for item in listed["tools"]
        ]
        tools = mcp_tools + [submit_tool_schema()]
        system = (
            "You are a software-maintenance agent operating on a pinned repository pack. "
            "You know nothing about the repository except what the MCP tools return. "
            "Use resource_info, then iterative search_resource and read_unit calls. "
            "Do not expose private chain-of-thought; optional assistant text before a tool "
            "call should be a one-sentence public action note. Never claim to have run the "
            "upstream test suite. Distinguish source facts, proposed changes, and risks. "
            "A ranked search hit is not evidence until you read its unit. For documentation, "
            "use only exact wording found in the captured quickstart: it states that exceeding "
            "the configured maximum raises TooManyRedirects, but gives no numeric default. "
            "Finish only by calling submit_deliverable."
        )
        task = (
            "Create an evidence-grounded maintainer impact brief for this proposed change: "
            "change Requests' library-wide default redirect ceiling from 30 to 20 while "
            "preserving per-Session overrides. Trace the constant definition, Session "
            "initialization, runtime enforcement, exception type, current default and custom "
            "limit tests, and user documentation. Recommend the smallest source/test/docs "
            "changes, call out what should not change, and attach a claim-evidence matrix. "
            "Use only the pinned pack; if capture truncation prevents a conclusion, say so."
        )
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]
        require_tool = False

        for _round in range(args.max_rounds):
            response = model_request(
                api_key=api_key,
                base_url=args.base_url,
                model=args.model,
                messages=messages,
                tools=tools,
                timeout=args.timeout,
                require_tool=require_tool,
            )
            # Save provider metadata and assistant message, never request headers/key.
            model_responses.append({
                "id": response.get("id"),
                "model": response.get("model"),
                "provider": response.get("provider"),
                "usage": response.get("usage", {}),
                "created": response.get("created"),
            })
            message = (response.get("choices") or [{}])[0].get("message") or {}
            assistant_message = {
                key: value for key, value in message.items()
                if key in {"role", "content", "tool_calls"}
            }
            messages.append(assistant_message)
            calls = message.get("tool_calls") or []
            if not calls:
                messages.append({
                    "role": "user",
                    "content": "Continue using tools and finish with submit_deliverable.",
                })
                require_tool = True
                continue
            require_tool = False
            for call in calls:
                call_id = call.get("id") or f"call-{len(steps) + 1:03d}"
                function = call.get("function") or {}
                name = function.get("name", "")
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                call_started = time.monotonic()
                if name == "submit_deliverable":
                    candidate_claims, errors = validate_submission(
                        arguments, searches=searches, reads=reads
                    )
                    if errors:
                        print(
                            "evidence gate rejected submission: " + "; ".join(errors),
                            file=sys.stderr,
                            flush=True,
                        )
                        payload = {
                            "accepted": False,
                            "validation_errors": errors,
                            "instruction": "Resolve every item with more MCP work, then resubmit.",
                        }
                        require_tool = True
                    else:
                        payload = {
                            "accepted": True,
                            "checks_passed": 8,
                            "claims_linked": len(candidate_claims),
                        }
                        submission = arguments
                        enriched_claims = candidate_claims
                    label = "Submit the maintainer brief"
                    observation = (
                        "Deliverable accepted by the evidence gate."
                        if payload["accepted"]
                        else "Evidence gate rejected the draft: " + "; ".join(errors)
                    )
                    selected: list[str] = []
                elif name in {"resource_info", "search_resource", "read_unit"}:
                    result = server.call("tools/call", {"name": name, "arguments": arguments})
                    payload = tool_payload(result)
                    if name == "search_resource" and "error" not in payload:
                        searches.append({"arguments": arguments, "payload": payload})
                    if name == "read_unit" and "error" not in payload:
                        reads[payload["unit_id"]] = payload
                    label, observation, selected = call_summary(name, arguments, payload)
                else:
                    payload = {"error": f"unknown tool {name!r}"}
                    label, observation, selected = name, payload["error"], []
                duration_ms = round((time.monotonic() - call_started) * 1000)
                exact_digest = sha256_bytes(canonical_bytes(payload))
                model_payload = compact_for_model(name, payload)
                steps.append({
                    "seq": len(steps) + 1,
                    "phase": (
                        "inspect" if name == "resource_info" else
                        "search" if name == "search_resource" else
                        "read" if name == "read_unit" else "deliver"
                    ),
                    "status": "passed" if "error" not in payload and payload.get("accepted", True) else "rejected",
                    "label": label,
                    "public_action_note": str(message.get("content") or "").strip(),
                    "tool": {
                        "name": name,
                        "call_id": call_id,
                        "arguments": arguments,
                        "duration_ms": duration_ms,
                        "result_sha256": exact_digest,
                        "result_excerpt": json.dumps(model_payload, ensure_ascii=False)[:1400],
                    },
                    "observation": observation,
                    "selected_unit_ids": selected,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": json.dumps(model_payload, ensure_ascii=False),
                })
            if submission is not None:
                break
        if submission is None:
            raise RuntimeError("model did not produce an accepted deliverable within the round limit")
    finally:
        server.close()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = RUN_DIR / "maintainer-impact-brief.md"
    artifact_path.write_text(submission["artifact_markdown"].rstrip() + "\n", encoding="utf-8")
    raw_transcript = {
        "schema_version": "1.0",
        "notice": "Public model messages and exact tool payloads; no hidden reasoning or credentials.",
        "messages": messages,
        "mcp_jsonrpc": server.raw_events,
        "model_responses": model_responses,
    }
    raw_path = RUN_DIR / "raw-transcript.json"
    raw_path.write_text(json.dumps(raw_transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for response in model_responses:
        item = response.get("usage") or {}
        for key in usage:
            usage[key] += int(item.get(key) or 0)
    finished_wall = datetime.now(timezone.utc)
    duration_ms = round((time.monotonic() - started) * 1000)
    checks = [
        {"id": "real_stdio_mcp", "passed": True, "detail": f"{len(server.raw_events)} JSON-RPC responses"},
        {"id": "iterative_search", "passed": len(searches) >= 4, "detail": f"{len(searches)} searches"},
        {"id": "five_required_units_read", "passed": len(reads) >= 5, "detail": f"{len(reads)} unique units"},
        {"id": "claim_citations_were_read", "passed": all(c["support"]["unit_id"] in reads for c in enriched_claims), "detail": f"{len(enriched_claims)} claims"},
        {"id": "artifact_written", "passed": artifact_path.is_file(), "detail": artifact_path.name},
        {"id": "credential_not_recorded", "passed": "sk-or-" not in raw_path.read_text(encoding="utf-8"), "detail": "credential marker absent"},
        {"id": "evidence_gate_accepted", "passed": True, "detail": "all required evidence roles covered"},
        {"id": "source_snapshot_still_matches", "passed": sha256_file(DEMO / "sources" / source["snapshot_file"]) == source["sha256"], "detail": source["sha256"]},
    ]
    run = {
        "schema_version": "1.0",
        "run_id": "requests-redirect-impact-llm",
        "title": "Plan a redirect-default change without missing its blast radius",
        "dek": "A model starts with no repository context, uses the generated MCP pack to trace six code and documentation roles, then submits a citation-gated maintainer brief.",
        "mode": "real-llm-tool-loop+mcp-stdio",
        "task": {
            "brief": task,
            "deliverables": ["Maintainer impact brief", "Claim-evidence matrix", "Risk and non-goals"],
            "constraints": ["Pinned Requests v2.34.2 pack only", "Read-only MCP", "No upstream test-suite claim"],
        },
        "recording": {
            "recorded_at": started_wall.isoformat().replace("+00:00", "Z"),
            "finished_at": finished_wall.isoformat().replace("+00:00", "Z"),
            "duration_ms": duration_ms,
            "provider": "OpenRouter-compatible chat completions",
            "model": model_responses[-1].get("model") or args.model,
            "model_calls": len(model_responses),
            "usage": usage,
            "tool_calls": len(steps),
            "search_calls": len(searches),
            "read_calls": sum(step["tool"]["name"] == "read_unit" for step in steps),
            "unique_units_read": len(reads),
        },
        "packs": [{
            "resource_id": "requests",
            "resource_type": "code",
            "origin_url": source["origin_url"],
            "version": source["version"],
            "snapshot_sha256": source["sha256"],
            "unit_count": 74,
        }],
        "steps": steps,
        "artifact": {
            "name": artifact_path.name,
            "media_type": "text/markdown",
            "sha256": sha256_file(artifact_path),
            "title": submission["title"],
            "summary": submission["summary"],
            "content": submission["artifact_markdown"],
            "limitations": submission["limitations"],
        },
        "claims": enriched_claims,
        "checks": checks,
        "verification": {
            "passed": all(item["passed"] for item in checks),
            "passed_count": sum(item["passed"] for item in checks),
            "total_count": len(checks),
            "raw_transcript": raw_path.name,
            "raw_transcript_sha256": sha256_file(raw_path),
            "replay_note": "MCP evidence can be replayed offline; model generation is not rerun in CI.",
        },
    }
    run_path = RUN_DIR / "run.json"
    run_path.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "run": str(run_path.relative_to(ROOT)),
        "model": run["recording"]["model"],
        "model_calls": run["recording"]["model_calls"],
        "tool_calls": run["recording"]["tool_calls"],
        "checks": f"{run['verification']['passed_count']}/{run['verification']['total_count']}",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
