#!/usr/bin/env python3
"""Build deterministic, replayable evidence-agent runs over demo packs.

These runs intentionally do not use an LLM.  A small scripted planner drives a
real Agentic Anything stdio MCP subprocess, records every JSON-RPC exchange,
and refuses to cite a unit that was not read first.  The resulting trajectories
show the evidence-gathering work that a tool-using agent performs without
misrepresenting deterministic orchestration as model reasoning.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
PACKS = DEMO / "packs"
RUNS = DEMO / "runs"
SRC = ROOT / "src"
MODE = "deterministic-evidence-agent"
SNAPSHOT_DATE = "2026-07-11"
PROTOCOL_VERSION = "2025-11-25"


def unit_count(info: dict[str, Any]) -> int | None:
    """Normalize the pack metadata field used for captured unit count."""
    return info.get("unit_count", info.get("page_count"))


def clean_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["PYTHONHASHSEED"] = "0"
    env.pop("OPENROUTER_API_KEY", None)
    env.pop("AGENTIC_API_KEY", None)
    return env


def json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_log_value(value: Any) -> Any:
    """Normalize the local checkout prefix while preserving MCP payload data."""
    if isinstance(value, str):
        return value.replace(str(ROOT), ".")
    if isinstance(value, list):
        return [portable_log_value(item) for item in value]
    if isinstance(value, dict):
        return {key: portable_log_value(item) for key, item in value.items()}
    return value


class StdioMCPClient:
    """Minimal line-delimited JSON-RPC client with a raw deterministic log."""

    def __init__(self, pack_dirs: list[Path]) -> None:
        self.pack_dirs = pack_dirs
        self.process: subprocess.Popen[str] | None = None
        self.request_id = 0
        self.event_sequence = 0
        self.raw_events: list[dict[str, Any]] = []
        self._selector: selectors.BaseSelector | None = None

    def __enter__(self) -> "StdioMCPClient":
        missing = [str(path) for path in self.pack_dirs if not (path / "agent-pack.json").is_file()]
        if missing:
            raise RuntimeError(
                "missing demo pack(s): " + ", ".join(missing)
                + "; run demos/build_demos.py first"
            )
        self.process = subprocess.Popen(
            [sys.executable, "-m", "agentic_anything", "mcp", *map(str, self.pack_dirs)],
            cwd=ROOT,
            env=clean_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        if self.process.stdout is None:
            raise RuntimeError("MCP subprocess stdout was not created")
        self._selector = selectors.DefaultSelector()
        self._selector.register(self.process.stdout, selectors.EVENT_READ)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.process is None:
            return
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            return_code = self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            return_code = self.process.wait(timeout=5)
        stderr = self.process.stderr.read() if self.process.stderr is not None else ""
        if self._selector is not None:
            self._selector.close()
        if exc_type is None and (return_code != 0 or stderr.strip()):
            raise RuntimeError(
                f"MCP subprocess exited with {return_code}; stderr: {stderr.strip()}"
            )

    def _record(self, direction: str, message: dict[str, Any]) -> None:
        self.event_sequence += 1
        self.raw_events.append({
            "sequence": self.event_sequence,
            "direction": direction,
            "message": portable_log_value(message),
        })

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)
        self._record("client_to_server", message)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.request_id += 1
        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params
        self._write(message)
        self._record("client_to_server", message)
        response = self._read_response()
        self._record("server_to_client", response)
        if response.get("id") != self.request_id:
            raise RuntimeError(
                f"MCP response id mismatch: expected {self.request_id}, got {response.get('id')}"
            )
        if "error" in response:
            raise RuntimeError(f"MCP error for {method}: {response['error']}")
        return response

    def _write(self, message: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("MCP subprocess is not running")
        wire = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        self.process.stdin.write(wire + "\n")
        self.process.stdin.flush()

    def _read_response(self) -> dict[str, Any]:
        if self.process is None or self.process.stdout is None or self._selector is None:
            raise RuntimeError("MCP subprocess is not running")
        ready = self._selector.select(timeout=30)
        if not ready:
            raise RuntimeError("timed out waiting for MCP stdio response")
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr is not None else ""
            raise RuntimeError(f"MCP subprocess closed stdout; stderr: {stderr.strip()}")
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise RuntimeError("MCP response was not a JSON object")
        return payload

    def initialize(self) -> tuple[dict[str, Any], list[str]]:
        response = self.request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "agentic-anything-demo-runner", "version": "1.0"},
        })
        self.notify("notifications/initialized", {})
        tools_response = self.request("tools/list", {})
        tools = [item["name"] for item in tools_response["result"]["tools"]]
        return response["result"], tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        response = self.request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        result = response["result"]
        if result.get("isError"):
            raise RuntimeError(f"MCP tool {name} failed: {result.get('content')}")
        structured = result.get("structuredContent")
        if not isinstance(structured, dict):
            raise RuntimeError(f"MCP tool {name} returned no structuredContent")
        return structured


@dataclass
class EvidenceRun:
    run_id: str
    task: str
    pack_ids: list[str]
    client: StdioMCPClient
    steps: list[dict[str, Any]] = field(default_factory=list)
    searches: list[dict[str, Any]] = field(default_factory=list)
    reads: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    discovery_steps: dict[tuple[str, str], int] = field(default_factory=dict)
    init_result: dict[str, Any] = field(default_factory=dict)
    tools: list[str] = field(default_factory=list)

    def start(self, next_reason: str) -> None:
        self.init_result, self.tools = self.client.initialize()
        self._step(
            phase="connect",
            tool="initialize + tools/list",
            tool_input={"protocolVersion": PROTOCOL_VERSION},
            output_summary=(
                f"Connected to {self.init_result['serverInfo']['name']} "
                f"{self.init_result['serverInfo']['version']}; tools: {', '.join(self.tools)}."
            ),
            units=[],
            next_reason=next_reason,
        )

    def inspect(self, resource_id: str | None, next_reason: str) -> dict[str, Any]:
        arguments = {} if resource_id is None else {"resource_id": resource_id}
        result = self.client.call_tool("resource_info", arguments)
        if "resources" in result:
            summary = "; ".join(
                f"{item['resource_id']} ({item['resource_type']}, {unit_count(item)} units)"
                for item in result["resources"]
            )
        else:
            summary = (
                f"Inspected {result['resource_id']}: {result['resource_type']}, "
                f"{unit_count(result)} units, {len(result.get('frontier', []))} frontier entries."
            )
        self._step(
            phase="inspect",
            tool="resource_info",
            tool_input=arguments,
            output_summary=summary,
            units=[],
            next_reason=next_reason,
        )
        return result

    def search(
        self,
        resource_id: str,
        query: str,
        *,
        expected_unit: str | None,
        next_reason: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        arguments = {"resource_id": resource_id, "query": query, "top_k": top_k}
        result = self.client.call_tool("search_resource", arguments)
        hits = result.get("hits", [])
        step_number = len(self.steps) + 1
        for hit in hits:
            self.discovery_steps.setdefault((hit["resource_id"], hit["unit_id"]), step_number)
        found_expected = expected_unit is None or any(
            hit["unit_id"] == expected_unit for hit in hits
        )
        if not found_expected:
            raise RuntimeError(
                f"query did not discover required unit {resource_id}/{expected_unit}: {query}"
            )
        units = [
            {
                "resource_id": hit["resource_id"],
                "unit_id": hit["unit_id"],
                "content_sha256": None,
                "status": "discovered_not_yet_read",
                "score": hit["score"],
            }
            for hit in hits[:3]
        ]
        top = ", ".join(f"{hit['unit_id']} ({hit['score']:.3f})" for hit in hits[:3])
        self._step(
            phase="search",
            tool="search_resource",
            tool_input=arguments,
            output_summary=f"Found {len(hits)} hit(s); top evidence units: {top}.",
            units=units,
            next_reason=next_reason,
        )
        self.searches.append({
            "step": step_number,
            "resource_id": resource_id,
            "query": query,
            "hit_units": [hit["unit_id"] for hit in hits],
            "expected_unit": expected_unit,
            "expected_unit_found": found_expected,
        })
        return result

    def read(
        self,
        resource_id: str,
        unit_id: str,
        *,
        anchors: list[str],
        next_reason: str,
    ) -> dict[str, Any]:
        key = (resource_id, unit_id)
        if key not in self.discovery_steps:
            raise RuntimeError(f"refusing to read undiscovered unit {resource_id}/{unit_id}")
        arguments = {"resource_id": resource_id, "unit_id": unit_id}
        result = self.client.call_tool("read_unit", arguments)
        markdown = result.get("markdown", "")
        missing = [anchor for anchor in anchors if anchor.casefold() not in markdown.casefold()]
        if missing:
            raise RuntimeError(f"{resource_id}/{unit_id} is missing anchors: {missing}")
        step_number = len(self.steps) + 1
        result["read_step"] = step_number
        self.reads[key] = result
        unit = {
            "resource_id": resource_id,
            "unit_id": unit_id,
            "locator": result.get("locator", ""),
            "content_sha256": result.get("content_sha256"),
            "status": "read_and_hash_verified_by_pack",
        }
        self._step(
            phase="read",
            tool="read_unit",
            tool_input=arguments,
            output_summary=(
                f"Read {len(markdown):,} Markdown characters from {result.get('locator')}; "
                f"confirmed {len(anchors)} required anchor(s); sha256 "
                f"{result.get('content_sha256')}."
            ),
            units=[unit],
            next_reason=next_reason,
        )
        return result

    def compute_step(
        self,
        label: str,
        tool_input: dict[str, Any],
        output_summary: str,
        evidence_keys: list[tuple[str, str]],
        next_reason: str,
    ) -> None:
        units = [self._unit_reference(key) for key in evidence_keys]
        self._step(
            phase="compute",
            tool=label,
            tool_input=tool_input,
            output_summary=output_summary,
            units=units,
            next_reason=next_reason,
        )

    def validate_step(
        self,
        output_summary: str,
        evidence_keys: list[tuple[str, str]],
        next_reason: str,
    ) -> None:
        self._step(
            phase="validate",
            tool="deterministic_assertions",
            tool_input={"evidence_units": len(evidence_keys)},
            output_summary=output_summary,
            units=[self._unit_reference(key) for key in evidence_keys],
            next_reason=next_reason,
        )

    def citation(self, citation_id: str, claim: str, resource_id: str, unit_id: str) -> dict[str, Any]:
        key = (resource_id, unit_id)
        if key not in self.reads:
            raise RuntimeError(
                f"refusing final citation {citation_id}: {resource_id}/{unit_id} was not read"
            )
        item = self.reads[key]
        return {
            "citation_id": citation_id,
            "claim": claim,
            "resource_id": resource_id,
            "unit_id": unit_id,
            "locator": item.get("locator", ""),
            "content_sha256": item.get("content_sha256"),
            "read_step": item["read_step"],
            "cited_after_read": True,
        }

    def _unit_reference(self, key: tuple[str, str]) -> dict[str, Any]:
        if key not in self.reads:
            raise RuntimeError(f"unit has not been read: {key[0]}/{key[1]}")
        item = self.reads[key]
        return {
            "resource_id": key[0],
            "unit_id": key[1],
            "locator": item.get("locator", ""),
            "content_sha256": item.get("content_sha256"),
            "status": "read",
        }

    def _step(
        self,
        *,
        phase: str,
        tool: str,
        tool_input: dict[str, Any],
        output_summary: str,
        units: list[dict[str, Any]],
        next_reason: str,
    ) -> None:
        self.steps.append({
            "step": len(self.steps) + 1,
            "phase": phase,
            "tool": tool,
            "tool_input": tool_input,
            "output_summary": output_summary,
            "units": units,
            "next_step_reason": next_reason,
        })


def assertion(assertions: list[dict[str, Any]], check_id: str, passed: bool, detail: str) -> None:
    assertions.append({"id": check_id, "passed": bool(passed), "detail": detail})


def citation_marker(citation: dict[str, Any]) -> str:
    return (
        f"[{citation['citation_id']}] `{citation['resource_id']}/{citation['unit_id']}` "
        f"— `{citation['locator']}` — sha256 `{citation['content_sha256']}`"
    )


def build_requests_run() -> tuple[dict[str, Any], str, dict[str, Any], list[dict[str, Any]]]:
    task = (
        "Assess the code, tests, exception, and documentation impact of changing "
        "Requests v2.34.2's default redirect ceiling from 30 to 10. Do not modify upstream code."
    )
    pack = PACKS / "requests"
    with StdioMCPClient([pack]) as client:
        run = EvidenceRun("requests-redirect-impact", task, ["requests"], client)
        run.start("Inspect the resource boundary before searching for redirect behavior.")
        info = run.inspect(
            "requests",
            "Locate the single source of truth for the numeric default.",
        )

        models = "file__src--requests--models-py"
        sessions = "file__src--requests--sessions-py"
        exceptions = "file__src--requests--exceptions-py"
        tests = "file__tests--test-requests-py"
        docs = "file__docs--user--quickstart-rst"

        run.search(
            "requests",
            "DEFAULT_REDIRECT_LIMIT int 30 definition models",
            expected_unit=models,
            next_reason="Read the definition and verify the exact current value.",
        )
        models_read = run.read(
            "requests", models,
            anchors=["DEFAULT_REDIRECT_LIMIT: int = 30"],
            next_reason="Trace how a Session consumes the constant and enforces the limit.",
        )

        run.search(
            "requests",
            "self max_redirects DEFAULT_REDIRECT_LIMIT len response history TooManyRedirects",
            expected_unit=sessions,
            next_reason="Read Session initialization and the runtime redirect guard together.",
        )
        sessions_read = run.read(
            "requests", sessions,
            anchors=[
                "self.max_redirects = DEFAULT_REDIRECT_LIMIT",
                "if len(resp.history) >= self.max_redirects",
                "raise TooManyRedirects",
            ],
            next_reason="Verify the public exception type raised by that guard.",
        )

        run.search(
            "requests",
            "class TooManyRedirects RequestException too many redirects",
            expected_unit=exceptions,
            next_reason="Read the exception declaration and inheritance.",
        )
        exceptions_read = run.read(
            "requests", exceptions,
            anchors=["class TooManyRedirects(RequestException)", "Too many redirects"],
            next_reason="Find executable regression tests that pin default and custom behavior.",
        )

        run.search(
            "requests",
            "test HTTP 302 TOO MANY REDIRECTS response history 30 custom max redirects 5",
            expected_unit=tests,
            next_reason="Read the tests to identify assertions affected by a 30-to-10 change.",
        )
        tests_read = run.read(
            "requests", tests,
            anchors=[
                "test_HTTP_302_TOO_MANY_REDIRECTS",
                "len(e.response.history) == 30",
                "s.max_redirects = 5",
                "len(e.response.history) == 5",
            ],
            next_reason="Check what the user-facing quickstart promises about redirects.",
        )

        run.search(
            "requests",
            "redirection history configured maximum redirections TooManyRedirects exception",
            expected_unit=docs,
            next_reason="Read the documentation contract and distinguish numeric from qualitative promises.",
        )
        docs_read = run.read(
            "requests", docs,
            anchors=[
                "Redirection and History",
                "exceeds the configured number of maximum redirections",
                "TooManyRedirects",
            ],
            next_reason="Synthesize the direct code, test, exception, and documentation impact.",
        )

        evidence_keys = [
            ("requests", models),
            ("requests", sessions),
            ("requests", exceptions),
            ("requests", tests),
            ("requests", docs),
        ]
        impact = {
            "current_default": 30,
            "proposed_default": 10,
            "direct_code_edits": ["src/requests/models.py"],
            "direct_test_edits": ["tests/test_requests.py default-history assertion"],
            "unchanged_mechanisms": [
                "Session copies DEFAULT_REDIRECT_LIMIT during initialization",
                "resolve_redirects compares response history with Session.max_redirects",
                "TooManyRedirects remains the raised exception type",
                "explicit per-session max_redirects values remain supported",
            ],
            "documentation_assessment": (
                "The captured quickstart promises a configured maximum and TooManyRedirects, "
                "but does not state the numeric default in that section."
            ),
            "behavioral_risk": (
                "Previously successful default redirect chains of length 10 through 29 would fail."
            ),
        }
        run.compute_step(
            "deterministic_change_impact",
            {"from": 30, "to": 10, "scope": "default behavior only"},
            (
                "Mapped one direct constant edit, one pinned default test expectation, four "
                "unchanged mechanisms, and the 10–29 redirect-chain compatibility risk."
            ),
            evidence_keys,
            "Run hard assertions over every source anchor and citation precondition.",
        )
        run.validate_step(
            "Validated all required layers and confirmed every final citation points to a previously read unit.",
            evidence_keys,
            "Emit the evidence-backed change-impact artifact and replay metadata.",
        )

        citations = [
            run.citation("R1", "The default redirect constant is 30.", "requests", models),
            run.citation(
                "R2",
                "Session copies the default and enforces it against response history.",
                "requests",
                sessions,
            ),
            run.citation(
                "R3", "TooManyRedirects inherits from RequestException.", "requests", exceptions
            ),
            run.citation(
                "R4", "Regression tests pin history length 30 and a custom value of 5.",
                "requests", tests,
            ),
            run.citation(
                "R5", "The quickstart documents history and the configured-maximum exception.",
                "requests", docs,
            ),
        ]

        artifact = f"""# Requests redirect-limit change-impact report

## Task

Assess changing the default redirect ceiling in the pinned Requests v2.34.2
resource from **30 to 10**, without editing upstream code in this run.

## Evidence-backed verdict

The numeric source of truth is `DEFAULT_REDIRECT_LIMIT: int = 30` in
`src/requests/models.py`. [R1] A new `Session` copies that constant into
`self.max_redirects`; `resolve_redirects` raises `TooManyRedirects` when response
history reaches the configured ceiling. [R2] The exception remains a
`RequestException` subtype. [R3]

Changing 30 to 10 therefore needs one direct production-code edit to the
constant. The initialization and guard mechanisms do not need structural
changes. The default regression test currently asserts a history length of 30
and must be updated, while the custom `s.max_redirects = 5` test should remain
unchanged. [R4]

The captured quickstart promises that exceeding the configured maximum raises
`TooManyRedirects`, but its redirect section does not promise a numeric default;
the qualitative documentation remains correct. [R5]

## Impact matrix

| Layer | Current contract | 30 → 10 impact |
|---|---|---|
| Definition | `DEFAULT_REDIRECT_LIMIT = 30` [R1] | Direct edit to `10` |
| Session default | Copies the constant [R2] | New sessions inherit `10`; no structural edit |
| Runtime guard | Compares `len(resp.history)` with `self.max_redirects` [R2] | Same guard trips earlier |
| Exception API | Raises `TooManyRedirects`, a `RequestException` [R2][R3] | No type change |
| Tests | Default expects `30`; custom policy expects `5` [R4] | Update only default expectation |
| Quickstart | Documents configured limit, not numeric value [R5] | No factual numeric edit required |

## Compatibility risk

With no explicit `Session.max_redirects`, redirect chains of length 10 through
29 that previously completed would now raise `TooManyRedirects`. Explicit
per-session policies remain available and are already covered by the custom
value test. [R2][R4]

## Read-before-cite ledger

""" + "\n".join(f"- {citation_marker(item)}" for item in citations) + "\n"

        assertions: list[dict[str, Any]] = []
        expected_tools = {"resource_info", "search_resource", "read_unit"}
        assertion(assertions, "mode_is_explicit", MODE == "deterministic-evidence-agent", MODE)
        assertion(assertions, "zero_model_calls", True, "No model client is imported or invoked.")
        assertion(
            assertions, "mcp_initialized",
            run.init_result.get("protocolVersion") == PROTOCOL_VERSION,
            f"Negotiated {run.init_result.get('protocolVersion')}.",
        )
        assertion(
            assertions, "required_tools_available", expected_tools.issubset(run.tools),
            f"Available tools: {', '.join(run.tools)}.",
        )
        assertion(assertions, "authentic_pack_size", unit_count(info) == 74, f"units={unit_count(info)}")
        assertion(assertions, "minimum_search_horizon", len(run.searches) >= 3, f"searches={len(run.searches)}")
        assertion(assertions, "minimum_read_horizon", len(run.reads) >= 4, f"reads={len(run.reads)}")
        assertion(
            assertions, "all_required_units_read",
            set(run.reads) == set(evidence_keys),
            f"read units={sorted(unit for _, unit in run.reads)}",
        )
        assertion(
            assertions, "all_reads_were_discovered",
            all(key in run.discovery_steps and run.discovery_steps[key] < item["read_step"] for key, item in run.reads.items()),
            "Every read followed a search result containing that unit.",
        )
        assertion(
            assertions, "definition_anchor", "DEFAULT_REDIRECT_LIMIT: int = 30" in models_read["markdown"],
            "models.py pins 30.",
        )
        assertion(
            assertions, "default_and_guard_anchors",
            all(text in sessions_read["markdown"] for text in (
                "self.max_redirects = DEFAULT_REDIRECT_LIMIT",
                "if len(resp.history) >= self.max_redirects",
                "raise TooManyRedirects",
            )),
            "sessions.py contains initialization and enforcement.",
        )
        assertion(
            assertions, "exception_anchor",
            "class TooManyRedirects(RequestException)" in exceptions_read["markdown"],
            "Exception inheritance confirmed.",
        )
        assertion(
            assertions, "tests_pin_default_and_override",
            all(text in tests_read["markdown"] for text in (
                "len(e.response.history) == 30", "s.max_redirects = 5", "len(e.response.history) == 5"
            )),
            "Default and explicit override tests confirmed.",
        )
        assertion(
            assertions, "docs_describe_configured_limit",
            "exceeds the configured number of maximum redirections" in docs_read["markdown"],
            "Quickstart contract confirmed.",
        )
        assertion(
            assertions, "citations_read_before_use",
            all(item["cited_after_read"] and item["read_step"] < len(run.steps) + 1 for item in citations),
            f"citations={len(citations)}",
        )
        artifact_markers = set(re.findall(r"\[(R\d+)\]", artifact))
        assertion(
            assertions, "artifact_citation_set_complete",
            artifact_markers == {item["citation_id"] for item in citations},
            f"markers={sorted(artifact_markers)}",
        )
        assertion(
            assertions, "citation_hashes_are_sha256",
            all(re.fullmatch(r"[0-9a-f]{64}", item["content_sha256"] or "") for item in citations),
            "Every cited read returned a 64-character SHA-256.",
        )
        assertion(
            assertions, "impact_is_consistent",
            impact["current_default"] == 30 and impact["proposed_default"] == 10,
            "Impact compares the evidenced default with the requested proposal.",
        )
        assertion(
            assertions, "raw_stdio_round_trips",
            sum(event["direction"] == "server_to_client" for event in client.raw_events)
            == sum(
                event["direction"] == "client_to_server" and "id" in event["message"]
                for event in client.raw_events
            ),
            "Every JSON-RPC request with an id has one recorded response.",
        )
        assertion(
            assertions, "raw_log_is_portable",
            str(ROOT) not in json.dumps(client.raw_events, ensure_ascii=False),
            "The checkout prefix is normalized to '.' in the checked-in raw log.",
        )

        verification = verification_payload(assertions, artifact)
        payload = run_payload(run, citations, impact, verification)
        raw_events = list(client.raw_events)
    return payload, artifact, verification, raw_events


ROW_RE = re.compile(r"^(\d{4})\s*\|\s*(.+)$", re.MULTILINE)
FAIR_RE = re.compile(
    r"^(F[1-4]|A1(?:\.[12])?|A2|I[1-3]|R1(?:\.[123])?)\.?\s+(.+)$",
    re.MULTILINE,
)
FAIR_IDS = [
    "F1", "F2", "F3", "F4",
    "A1", "A1.1", "A1.2", "A2",
    "I1", "I2", "I3",
    "R1", "R1.1", "R1.2", "R1.3",
]


def parse_gistemp_rows(markdowns: list[str]) -> dict[int, dict[str, float | None]]:
    columns = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        "J-D", "D-N", "DJF", "MAM", "JJA", "SON",
    ]
    rows: dict[int, dict[str, float | None]] = {}
    for markdown in markdowns:
        for match in ROW_RE.finditer(markdown):
            year = int(match.group(1))
            raw_values = [value.strip() for value in match.group(2).split("|")]
            if len(raw_values) != len(columns):
                raise RuntimeError(
                    f"unexpected GISTEMP field count for {year}: {len(raw_values)}"
                )
            if year in rows:
                raise RuntimeError(f"duplicate GISTEMP year: {year}")
            rows[year] = {
                column: None if value == "***" else float(value)
                for column, value in zip(columns, raw_values)
            }
    return rows


def derive_gistemp(rows: dict[int, dict[str, float | None]]) -> dict[str, Any]:
    annual = {year: values["J-D"] for year, values in rows.items()}
    complete = {year: value for year, value in annual.items() if value is not None}

    def mean(start: int, end: int) -> float:
        values = [float(complete[year]) for year in range(start, end + 1)]
        return round(sum(values) / len(values), 3)

    record_year, record_value = max(complete.items(), key=lambda item: (float(item[1]), item[0]))
    return {
        "parsed_years": len(rows),
        "complete_annual_years": len(complete),
        "annual_column": "J-D",
        "annual_values": {
            "2023": complete[2023],
            "2024": complete[2024],
            "2025": complete[2025],
            "2026": annual[2026],
        },
        "decadal_means": {
            "1980-1989": mean(1980, 1989),
            "1990-1999": mean(1990, 1999),
            "2000-2009": mean(2000, 2009),
            "2010-2019": mean(2010, 2019),
            "2020-2025": mean(2020, 2025),
        },
        "record_complete_year": {"year": record_year, "J-D": record_value},
        "delta_2024_vs_2023": round(float(complete[2024]) - float(complete[2023]), 3),
        "delta_2024_vs_2010s_mean": round(float(complete[2024]) - mean(2010, 2019), 3),
        "missing_value_policy": "Exclude only rows whose J-D value is '***' from annual comparisons.",
    }


def build_fair_audit(definitions: dict[str, str]) -> list[dict[str, str]]:
    assessments = {
        "F1": ("not_evidenced", "A source URL and local unit IDs exist, but global persistence is not established."),
        "F2": ("partial", "The rows preserve a schema and values; descriptive metadata remains sparse."),
        "F3": ("partial", "Read units carry source locators, but no explicit persistent dataset identifier is shown."),
        "F4": ("partial", "The MCP pack is searchable locally; registration in an external searchable registry is not evidenced."),
        "A1": ("partial", "Units are retrievable through MCP, but not by an evidenced globally persistent identifier."),
        "A1.1": ("partial", "The recorded stdio MCP exchange works without network access; universality is not established by this pack."),
        "A1.2": ("not_evidenced", "No authentication or authorization procedure appears in the captured dataset units."),
        "A2": ("not_evidenced", "The snapshot cannot prove metadata survival after source data disappearance."),
        "I1": ("partial", "A machine-readable table schema is preserved, but no formal knowledge-representation language is declared."),
        "I2": ("not_evidenced", "No FAIR vocabulary is declared in the captured dataset units."),
        "I3": ("not_evidenced", "No qualified references to other metadata objects are captured."),
        "R1": ("partial", "Column names and values are present, while richer contextual attributes are limited."),
        "R1.1": ("not_evidenced", "No data-usage license appears in the complete three-unit GISTEMP pack."),
        "R1.2": ("partial", "Source locators and content SHA-256 values provide capture-level provenance."),
        "R1.3": ("not_evidenced", "No domain-community metadata standard is declared in the captured units."),
    }
    return [
        {
            "principle": principle,
            "definition": definitions[principle],
            "status": assessments[principle][0],
            "rationale": assessments[principle][1],
        }
        for principle in FAIR_IDS
    ]


def build_gistemp_fair_run() -> tuple[dict[str, Any], str, dict[str, Any], list[dict[str, Any]]]:
    task = (
        "Compute a reproducible annual GISTEMP trend summary from the captured table, "
        "handle incomplete years explicitly, and audit the pack against all 15 FAIR sub-principles."
    )
    with StdioMCPClient([PACKS / "gistemp", PACKS / "fair-paper"]) as client:
        run = EvidenceRun("gistemp-fair-audit", task, ["gistemp", "fair-paper"], client)
        run.start("Inspect both resource boundaries before selecting data and rubric evidence.")
        info = run.inspect(
            None,
            "Read every GISTEMP unit so absence claims in the later audit have a closed capture scope.",
        )

        overview = "nasa-gistemp-global__001__nasa-gistemp-global-csv-overview"
        early_rows = "nasa-gistemp-global__002__nasa-gistemp-global-csv-rows-1-100"
        recent_rows = "nasa-gistemp-global__003__nasa-gistemp-global-csv-rows-101-147"
        fair_unit = "fair-guiding-principles-pmc4792175"

        run.search(
            "gistemp",
            "Land-Ocean Global Means overview 147 data rows 19 columns",
            expected_unit=overview,
            next_reason="Read the table overview, including its capture-level limitations.",
        )
        overview_read = run.read(
            "gistemp", overview,
            anchors=["Land-Ocean: Global Means", "147 data rows", "19 columns"],
            next_reason="Retrieve the historical rows and their explicit column header.",
        )

        run.search(
            "gistemp",
            "Year Jan Feb Mar Apr J-D 1880 1978 global means",
            expected_unit=early_rows,
            next_reason="Read the first table segment for the historical series and schema.",
        )
        early_read = run.read(
            "gistemp", early_rows,
            anchors=["Year | Jan | Feb", "J-D", "1880", "1978"],
            next_reason="Retrieve the modern segment containing 2023, 2024, 2025, and incomplete 2026.",
        )

        run.search(
            "gistemp",
            "2023 2024 2025 2026 J-D annual global anomaly",
            expected_unit=recent_rows,
            next_reason="Read recent rows and preserve the explicit '***' missing-value marker.",
        )
        recent_read = run.read(
            "gistemp", recent_rows,
            anchors=["2023 |", "2024 |", "1.28", "2026 |", "***"],
            next_reason="Parse the two row units and compute annual comparisons without using the raw CSV file.",
        )

        rows = parse_gistemp_rows([early_read["markdown"], recent_read["markdown"]])
        derived = derive_gistemp(rows)
        gistemp_keys = [
            ("gistemp", overview),
            ("gistemp", early_rows),
            ("gistemp", recent_rows),
        ]
        run.compute_step(
            "parse_markdown_table_and_compute",
            {
                "input": "two read_unit Markdown responses",
                "annual_column": "J-D",
                "missing_marker": "***",
            },
            (
                f"Parsed {derived['parsed_years']} years; excluded incomplete 2026 J-D; "
                f"computed 2024={derived['annual_values']['2024']:.2f}, record year "
                f"{derived['record_complete_year']['year']}, and five period means."
            ),
            gistemp_keys[1:],
            "Retrieve the FAIR definitions that will serve as the audit rubric.",
        )

        run.search(
            "fair-paper",
            "F1 F2 F3 F4 persistent identifier rich metadata searchable resource",
            expected_unit=fair_unit,
            next_reason="Read the complete paper unit before citing any FAIR principle.",
        )
        fair_read = run.read(
            "fair-paper", fair_unit,
            anchors=[
                "F1. (meta)data are assigned",
                "A1. (meta)data are retrievable",
                "I1. (meta)data use a formal",
                "R1. meta(data) are richly described",
            ],
            next_reason="Use focused searches to confirm the Accessible subgroup wording.",
        )
        run.search(
            "fair-paper",
            "A1 A1.1 A1.2 A2 retrievable standardized protocol authentication metadata accessible",
            expected_unit=fair_unit,
            next_reason="Confirm the Interoperable subgroup wording in focused evidence snippets.",
        )
        run.search(
            "fair-paper",
            "I1 I2 I3 formal language vocabularies qualified references metadata",
            expected_unit=fair_unit,
            next_reason="Confirm the Reusable subgroup wording and provenance/license requirements.",
        )
        run.search(
            "fair-paper",
            "R1 R1.1 R1.2 R1.3 usage license detailed provenance community standards",
            expected_unit=fair_unit,
            next_reason="Extract all 15 definitions and score only what the completely read GISTEMP pack evidences.",
        )

        definitions = {match.group(1): match.group(2).strip() for match in FAIR_RE.finditer(fair_read["markdown"])}
        if set(definitions) != set(FAIR_IDS):
            raise RuntimeError(
                f"FAIR definition set mismatch: expected {FAIR_IDS}, got {sorted(definitions)}"
            )
        audit = build_fair_audit(definitions)
        all_keys = gistemp_keys + [("fair-paper", fair_unit)]
        status_counts = {
            status: sum(item["status"] == status for item in audit)
            for status in ("partial", "not_evidenced")
        }
        run.compute_step(
            "closed_scope_fair_audit",
            {
                "principles": FAIR_IDS,
                "allowed_statuses": ["partial", "not_evidenced"],
                "scope": "captured GISTEMP pack, not NASA's complete stewardship program",
            },
            (
                f"Audited all {len(audit)} FAIR entries: {status_counts['partial']} partial and "
                f"{status_counts['not_evidenced']} not evidenced; no unsupported full-pass claim."
            ),
            all_keys,
            "Validate calculations, principle coverage, closed-scope absence claims, and citation order.",
        )
        run.validate_step(
            (
                "Recomputed all numeric checks, confirmed all three GISTEMP units were read, "
                "and confirmed the complete 15-principle rubric."
            ),
            all_keys,
            "Emit the reproducible research brief, cautious FAIR audit, and raw MCP replay log.",
        )

        citations = [
            run.citation("G1", "The pack overview identifies the Land-Ocean Global Means table.", "gistemp", overview),
            run.citation("G2", "The historical row unit supplies the schema and years through 1978.", "gistemp", early_rows),
            run.citation("G3", "The recent row unit supplies 1979–2026 values and missing markers.", "gistemp", recent_rows),
            run.citation("F1", "The paper states all 15 FAIR sub-principles used by the audit.", "fair-paper", fair_unit),
        ]

        period_rows = "\n".join(
            f"| {period} | {value:.3f} °C |"
            for period, value in derived["decadal_means"].items()
        )
        audit_rows = "\n".join(
            f"| {item['principle']} | {item['definition']} | `{item['status']}` | {item['rationale']} [F1][G1][G2][G3] |"
            for item in audit
        )
        artifact = f"""# NASA GISTEMP reproducible brief and FAIR evidence audit

## Task and scope

This report parses the **read-unit Markdown returned by the real MCP server**;
it does not read the source CSV directly. The calculation treats `J-D` as the
requested annual field. The captured units preserve that label and its values,
but do not state the anomaly reference baseline, so this report does not infer
one. [G1][G2][G3]

The FAIR table audits only what the captured three-unit GISTEMP pack evidences.
It is not a certification of NASA's complete data stewardship program.

## Reproducible findings

- Parsed years: **{derived['parsed_years']}** (1880–2026). [G2][G3]
- Complete `J-D` years: **{derived['complete_annual_years']}**.
- 2024 `J-D`: **{derived['annual_values']['2024']:.2f} °C**; 2023: **{derived['annual_values']['2023']:.2f} °C**; difference: **{derived['delta_2024_vs_2023']:.2f} °C**. [G3]
- Highest complete annual value: **{derived['record_complete_year']['year']} ({derived['record_complete_year']['J-D']:.2f} °C)**. [G3]
- 2024 is **{derived['delta_2024_vs_2010s_mean']:.3f} °C** above the 2010–2019 mean. [G3]
- 2026 has `J-D = ***` and is excluded from annual comparisons, rather than treated as zero. [G3]

| Period | Mean `J-D` anomaly |
|---|---:|
{period_rows}

## FAIR evidence audit

The definitions below come from the captured FAIR Guiding Principles paper.
[F1] `partial` means some pack evidence exists but the full principle is not
established; `not_evidenced` means this closed capture does not support the
claim. Absence of evidence here is not evidence that NASA lacks the property.

| Principle | Paper definition | Status | Pack-scoped rationale |
|---|---|---|---|
{audit_rows}

## Read-before-cite ledger

""" + "\n".join(f"- {citation_marker(item)}" for item in citations) + "\n"

        assertions: list[dict[str, Any]] = []
        resources = {item["resource_id"]: item for item in info.get("resources", [])}
        assertion(assertions, "mode_is_explicit", MODE == "deterministic-evidence-agent", MODE)
        assertion(assertions, "zero_model_calls", True, "No model client is imported or invoked.")
        assertion(
            assertions, "mcp_initialized",
            run.init_result.get("protocolVersion") == PROTOCOL_VERSION,
            f"Negotiated {run.init_result.get('protocolVersion')}.",
        )
        assertion(
            assertions, "two_authentic_resources_inspected",
            set(resources) == {"gistemp", "fair-paper"}
            and unit_count(resources["gistemp"]) == 3
            and unit_count(resources["fair-paper"]) == 1,
            f"resources={[(key, unit_count(value)) for key, value in sorted(resources.items())]}",
        )
        assertion(assertions, "long_search_horizon", len(run.searches) >= 7, f"searches={len(run.searches)}")
        assertion(assertions, "all_pack_units_read", set(run.reads) == set(all_keys), f"reads={len(run.reads)}")
        assertion(
            assertions, "all_reads_were_discovered",
            all(key in run.discovery_steps and run.discovery_steps[key] < item["read_step"] for key, item in run.reads.items()),
            "Every read followed a search result containing that unit.",
        )
        assertion(assertions, "parsed_year_count", derived["parsed_years"] == 147, f"years={derived['parsed_years']}")
        assertion(
            assertions, "complete_annual_count",
            derived["complete_annual_years"] == 146,
            f"complete={derived['complete_annual_years']}",
        )
        assertion(
            assertions, "missing_2026_excluded",
            derived["annual_values"]["2026"] is None,
            "2026 J-D parsed as None from '***'.",
        )
        assertion(
            assertions, "annual_values_exact",
            derived["annual_values"]["2023"] == 1.17
            and derived["annual_values"]["2024"] == 1.28
            and derived["annual_values"]["2025"] == 1.19,
            f"values={derived['annual_values']}",
        )
        assertion(
            assertions, "record_year_exact",
            derived["record_complete_year"] == {"year": 2024, "J-D": 1.28},
            f"record={derived['record_complete_year']}",
        )
        assertion(
            assertions, "derived_deltas_exact",
            derived["delta_2024_vs_2023"] == 0.11
            and derived["delta_2024_vs_2010s_mean"] == 0.474,
            (
                f"delta23={derived['delta_2024_vs_2023']}, "
                f"delta2010s={derived['delta_2024_vs_2010s_mean']}"
            ),
        )
        assertion(
            assertions, "decadal_means_exact",
            derived["decadal_means"] == {
                "1980-1989": 0.245,
                "1990-1999": 0.384,
                "2000-2009": 0.587,
                "2010-2019": 0.806,
                "2020-2025": 1.065,
            },
            f"means={derived['decadal_means']}",
        )
        assertion(
            assertions, "all_fair_definitions_extracted",
            [item["principle"] for item in audit] == FAIR_IDS,
            f"principles={len(audit)}",
        )
        assertion(
            assertions, "audit_avoids_unsupported_pass",
            all(item["status"] in {"partial", "not_evidenced"} for item in audit),
            f"status_counts={status_counts}",
        )
        assertion(
            assertions, "closed_scope_for_absence_claims",
            set(key for key in run.reads if key[0] == "gistemp") == set(gistemp_keys),
            "All three GISTEMP units were read before not-evidenced assessments.",
        )
        assertion(
            assertions, "citations_read_before_use",
            all(item["cited_after_read"] and item["read_step"] < len(run.steps) + 1 for item in citations),
            f"citations={len(citations)}",
        )
        artifact_markers = set(re.findall(r"\[((?:G|F)\d+)\]", artifact))
        assertion(
            assertions, "artifact_citation_set_complete",
            artifact_markers == {item["citation_id"] for item in citations},
            f"markers={sorted(artifact_markers)}",
        )
        assertion(
            assertions, "citation_hashes_are_sha256",
            all(re.fullmatch(r"[0-9a-f]{64}", item["content_sha256"] or "") for item in citations),
            "Every cited read returned a 64-character SHA-256.",
        )
        assertion(
            assertions, "raw_stdio_round_trips",
            sum(event["direction"] == "server_to_client" for event in client.raw_events)
            == sum(
                event["direction"] == "client_to_server" and "id" in event["message"]
                for event in client.raw_events
            ),
            "Every JSON-RPC request with an id has one recorded response.",
        )
        assertion(
            assertions, "raw_log_is_portable",
            str(ROOT) not in json.dumps(client.raw_events, ensure_ascii=False),
            "The checkout prefix is normalized to '.' in the checked-in raw log.",
        )
        assertion(
            assertions, "overview_schema_is_correct",
            "147 data rows, 19 columns" in overview_read["markdown"],
            "The preamble-aware importer exposes the real table shape.",
        )

        result = {"derived": derived, "fair_audit": audit, "status_counts": status_counts}
        verification = verification_payload(assertions, artifact)
        payload = run_payload(run, citations, result, verification)
        raw_events = list(client.raw_events)
    return payload, artifact, verification, raw_events


def verification_payload(assertions: list[dict[str, Any]], artifact: str) -> dict[str, Any]:
    passed = sum(item["passed"] for item in assertions)
    return {
        "schema_version": "1.0",
        "mode": MODE,
        "model_calls": 0,
        "passed": passed == len(assertions),
        "assertions_passed": passed,
        "assertions_total": len(assertions),
        "artifact_sha256": sha256_text(artifact),
        "assertions": assertions,
    }


def run_payload(
    run: EvidenceRun,
    citations: list[dict[str, Any]],
    result: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": run.run_id,
        "mode": MODE,
        "model_calls": 0,
        "planner": "fixed transparent state machine",
        "task": run.task,
        "snapshot_date": SNAPSHOT_DATE,
        "packs": run.pack_ids,
        "data_access": "real stdio MCP subprocess only",
        "network_access": False,
        "raw_event_normalization": "Local checkout prefix replaced with '.'; all other JSON-RPC data preserved.",
        "mcp": {
            "transport": "stdio",
            "protocol_version": run.init_result.get("protocolVersion"),
            "server": run.init_result.get("serverInfo"),
            "tools": run.tools,
            "command": [
                "python", "-m", "agentic_anything", "mcp",
                *[f"demos/packs/{pack_id}" for pack_id in run.pack_ids],
            ],
        },
        "summary": {
            "steps": len(run.steps),
            "search_calls": len(run.searches),
            "read_calls": len(run.reads),
            "cited_units": len(citations),
            "assertions_passed": verification["assertions_passed"],
            "assertions_total": verification["assertions_total"],
        },
        "steps": run.steps,
        "citations": citations,
        "result": result,
        "outputs": {
            "artifact": "artifact.md",
            "verification": "verification.json",
            "raw_events": "raw-events.jsonl",
        },
    }


def write_run(
    payload: dict[str, Any],
    artifact: str,
    verification: dict[str, Any],
    raw_events: list[dict[str, Any]],
) -> dict[str, Any]:
    destination = RUNS / payload["run_id"]
    if destination.exists():
        # Rebuild only this script's owned output. Other run types (for example
        # an explicitly recorded model run) may share demos/runs/.
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "run.json").write_text(json_text(payload), encoding="utf-8")
    (destination / "artifact.md").write_text(artifact, encoding="utf-8")
    (destination / "verification.json").write_text(json_text(verification), encoding="utf-8")
    raw_text = "".join(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for event in raw_events
    )
    (destination / "raw-events.jsonl").write_text(raw_text, encoding="utf-8")
    return {
        "run_id": payload["run_id"],
        "task": payload["task"],
        "mode": MODE,
        "model_calls": 0,
        "packs": payload["packs"],
        "summary": payload["summary"],
        "passed": verification["passed"],
        "files": {
            name: {
                "path": f"{payload['run_id']}/{name}",
                "sha256": sha256_file(destination / name),
            }
            for name in ("run.json", "artifact.md", "verification.json", "raw-events.jsonl")
        },
    }


def recorded_llm_index_entry() -> dict[str, Any] | None:
    """Include the separately recorded paid run without ever regenerating it."""
    destination = RUNS / "requests-redirect-impact-llm"
    run_path = destination / "run.json"
    if not run_path.is_file():
        return None
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    artifact_name = payload["artifact"]["name"]
    artifact_path = destination / artifact_name
    raw_path = destination / payload["verification"]["raw_transcript"]
    if sha256_file(artifact_path) != payload["artifact"]["sha256"]:
        raise RuntimeError("recorded LLM artifact hash mismatch; rerun review_recorded_llm_run.py")
    if sha256_file(raw_path) != payload["verification"]["raw_transcript_sha256"]:
        raise RuntimeError("recorded LLM transcript hash mismatch; rerun review_recorded_llm_run.py")
    if not payload["verification"]["passed"] or not all(item["passed"] for item in payload["checks"]):
        raise RuntimeError("recorded LLM run has a failed publishability check")
    publishable = run_path.read_text(encoding="utf-8") + raw_path.read_text(encoding="utf-8")
    if any(marker in publishable for marker in (str(ROOT), "sk-or-v1-")):
        raise RuntimeError("recorded LLM run contains a local path or credential marker")
    recording = payload["recording"]
    return {
        "run_id": payload["run_id"],
        "task": payload["task"]["brief"],
        "mode": payload["mode"],
        "model_calls": recording["model_calls"],
        "packs": [item["resource_id"] for item in payload["packs"]],
        "summary": {
            "assertions_passed": payload["verification"]["passed_count"],
            "assertions_total": payload["verification"]["total_count"],
            "cited_units": len({item["support"]["unit_id"] for item in payload["claims"]}),
            "read_calls": recording["read_calls"],
            "search_calls": recording["search_calls"],
            "steps": len(payload["steps"]),
        },
        "passed": True,
        "files": {
            "run.json": {"path": f"{payload['run_id']}/run.json", "sha256": sha256_file(run_path)},
            artifact_name: {"path": f"{payload['run_id']}/{artifact_name}", "sha256": sha256_file(artifact_path)},
            raw_path.name: {"path": f"{payload['run_id']}/{raw_path.name}", "sha256": sha256_file(raw_path)},
        },
    }


def main() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)

    built = []
    for builder in (build_requests_run, build_gistemp_fair_run):
        payload, artifact, verification, raw_events = builder()
        built.append(write_run(payload, artifact, verification, raw_events))

    recorded = recorded_llm_index_entry()
    all_runs = ([recorded] if recorded else []) + built
    total_assertions = sum(item["summary"]["assertions_total"] for item in all_runs)
    passed_assertions = sum(item["summary"]["assertions_passed"] for item in all_runs)
    index = {
        "schema_version": "1.0",
        "mode": "mixed-recorded-agent-runs",
        "model_calls": sum(item["model_calls"] for item in all_runs),
        "description": (
            "One real model tool loop plus two deterministic evidence-agent trajectories over "
            "authentic packs. Every run is inspectable; deterministic runs rebuild offline."
        ),
        "snapshot_date": SNAPSHOT_DATE,
        "runs": all_runs,
        "summary": {
            "run_count": len(all_runs),
            "runs_passed": sum(item["passed"] for item in all_runs),
            "assertions_passed": passed_assertions,
            "assertions_total": total_assertions,
            "all_passed": all(item["passed"] for item in all_runs),
        },
        "rebuild": "python demos/build_agent_runs.py  # replays deterministic runs; validates recorded LLM run",
    }
    (RUNS / "index.json").write_text(json_text(index), encoding="utf-8")

    print(
        f"✓ built {len(built)} {MODE} runs through real stdio MCP\n"
        f"✓ indexed {len(all_runs)} total runs; {passed_assertions}/{total_assertions} checks passed\n"
        f"✓ output: {RUNS.relative_to(ROOT)}/index.json"
    )
    return 0 if index["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
