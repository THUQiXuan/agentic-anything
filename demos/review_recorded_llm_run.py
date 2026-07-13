#!/usr/bin/env python3
"""Deterministically review the checked-in LLM recording.

The source of truth is the last ``submit_deliverable`` call whose recorded tool
result says ``accepted: true`` in ``raw-transcript.json``.  This script extracts
that model draft verbatim, applies a small exact-once semantic patch, and writes
both the preserved draft and reviewed artifact.  It never uses a previously
reviewed artifact as input, so deleting or corrupting the artifact and rerunning
this script produces the same reviewed bytes from the raw recording.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "demos" / "runs" / "requests-redirect-impact-llm"
RUN_PATH = RUN_DIR / "run.json"
RAW_PATH = RUN_DIR / "raw-transcript.json"
DRAFT_PATH = RUN_DIR / "accepted-model-draft.md"
ARTIFACT_PATH = RUN_DIR / "maintainer-impact-brief.md"
PACK_PAGES = ROOT / "demos" / "packs" / "requests" / "pages"

QUICKSTART_UNIT = "file__docs--user--quickstart-rst"
ADVANCED_UNIT = "file__docs--user--advanced-rst"
EXCEPTIONS_UNIT = "file__src--requests--exceptions-py"
SESSIONS_UNIT = "file__src--requests--sessions-py"
TRANSFORM_ID = "requests-redirect-semantic-review-v1"


# Each replacement is intentionally exact and must occur once.  A changed raw
# draft therefore fails loudly instead of silently applying a fuzzy editorial
# rewrite.
REPLACEMENTS = (
    (
        "replace-unsupported-docs-section",
        """6. User Documentation:
- In `docs/user/quickstart.rst`, the redirection behavior is documented, including the use of `allow_redirects` parameter and the `Response.history` property.
- The default redirect limit is not explicitly stated but the behavior of redirects and history is described.
- In `docs/user/advanced.rst`, the Session object and its attributes including `max_redirects` are documented, with explanation that the limit can be overridden per Session.""",
        """6. User Documentation:
- In `docs/user/quickstart.rst`, the redirection behavior is documented, including the use of the `allow_redirects` parameter and the `Response.history` property.
- The same captured unit states that exceeding the configured maximum raises `TooManyRedirects`.
- The captured user documentation does not explicitly state the numeric default, so the pack does not support claiming that “30” is part of the documented public contract.""",
    ),
    (
        "replace-unsupported-docs-recommendation",
        "- Update or add a note in the user documentation (`docs/user/advanced.rst` and optionally `docs/user/quickstart.rst`) to reflect the new default redirect limit of 20.",
        "- If maintainers want the numeric default to become part of the documented contract, add a note to `docs/user/quickstart.rst`; its current qualitative statement remains correct without an edit.",
    ),
    (
        "split-raise-and-exception-type-matrix-row",
        "| TooManyRedirects exception raised on exceeding redirects   | src/requests/sessions.py, src/requests/exceptions.py |",
        "| TooManyRedirects is raised when the count exceeds self.max_redirects | src/requests/sessions.py |\n| TooManyRedirects is defined as a RequestException subtype | src/requests/exceptions.py |",
    ),
    (
        "remove-unsupported-advanced-docs-matrix-row",
        "| User docs describe Session and max_redirects attribute     | docs/user/advanced.rst                       |\n",
        "",
    ),
    (
        "tighten-quickstart-matrix-row",
        "| User docs describe redirect behavior and history           | docs/user/quickstart.rst                      |",
        "| User docs state that exceeding the configured maximum raises TooManyRedirects | docs/user/quickstart.rst |",
    ),
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(value.encode("utf-8"))


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def portable(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(str(ROOT), ".")
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    return value


def json_object(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} is not a JSON object")
    return value


def accepted_submission(raw: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return the final recorded submission whose paired tool result accepted it."""
    results: dict[str, dict[str, Any]] = {}
    for message in raw.get("messages", []):
        if message.get("role") != "tool" or message.get("name") != "submit_deliverable":
            continue
        call_id = str(message.get("tool_call_id") or "")
        results[call_id] = json_object(message.get("content"), f"tool result {call_id}")

    accepted: list[tuple[str, dict[str, Any]]] = []
    for message in raw.get("messages", []):
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            if function.get("name") != "submit_deliverable":
                continue
            call_id = str(call.get("id") or "")
            if results.get(call_id, {}).get("accepted") is True:
                accepted.append((call_id, json_object(function.get("arguments"), f"arguments {call_id}")))
    if not accepted:
        raise RuntimeError("raw transcript contains no accepted submit_deliverable call")
    return accepted[-1]


def recorded_model_tool_calls(raw: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    calls: list[tuple[str, str, dict[str, Any]]] = []
    for message in raw.get("messages", []):
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            calls.append((
                str(call.get("id") or ""),
                str(function.get("name") or ""),
                json_object(function.get("arguments"), "recorded tool arguments"),
            ))
    return calls


def quickstart_lineage(raw: dict[str, Any]) -> dict[str, Any]:
    """Prove quickstart was gate-directed, not discovered by ranked search."""
    search_hits: set[str] = set()
    first_read_request: int | None = None
    for index, event in enumerate(raw.get("mcp_jsonrpc", []), 1):
        request = event.get("request") or {}
        if request.get("method") != "tools/call":
            continue
        params = request.get("params") or {}
        arguments = params.get("arguments") or {}
        if params.get("name") == "search_resource":
            structured = ((event.get("response") or {}).get("result") or {}).get("structuredContent") or {}
            search_hits.update(str(item.get("unit_id")) for item in structured.get("hits", []))
        if params.get("name") == "read_unit" and arguments.get("unit_id") == QUICKSTART_UNIT:
            first_read_request = index
            break
    if first_read_request is None:
        raise RuntimeError("quickstart was not read in the raw MCP transcript")
    if QUICKSTART_UNIT in search_hits:
        raise RuntimeError("quickstart lineage changed: it was search-discovered before its first read")

    gate_call_id = ""
    for message in raw.get("messages", []):
        if message.get("role") != "tool" or message.get("name") != "submit_deliverable":
            continue
        payload = json_object(message.get("content"), "submit_deliverable result")
        if payload.get("accepted") is False and QUICKSTART_UNIT in json.dumps(payload, ensure_ascii=False):
            gate_call_id = str(message.get("tool_call_id") or "")
            break
    if not gate_call_id:
        raise RuntimeError("no rejected evidence-gate result explicitly requires quickstart")
    return {
        "unit_id": QUICKSTART_UNIT,
        "path": "evidence-gate-directed-read",
        "search_discovered_before_first_read": False,
        "gate_submit_call_id": gate_call_id,
        "raw_mcp_first_read_event": first_read_request,
        "note": (
            "The first submission's evidence gate named this required docs unit. "
            "The model then read it directly; none of the preceding ranked searches returned it."
        ),
    }


def correct_draft(draft: str) -> tuple[str, list[dict[str, Any]]]:
    corrected = draft
    operations: list[dict[str, Any]] = []
    for operation_id, old, new in REPLACEMENTS:
        occurrences = corrected.count(old)
        if occurrences != 1:
            raise RuntimeError(
                f"{operation_id} expected exactly one raw-draft match; found {occurrences}"
            )
        corrected = corrected.replace(old, new, 1)
        operations.append({
            "operation_id": operation_id,
            "match_count": occurrences,
            "before_sha256": digest_text(old),
            "after_sha256": digest_text(new),
        })
    corrected = corrected.rstrip("\n") + "\n"
    return corrected, operations


def unit_support(unit_id: str) -> dict[str, str]:
    page = json.loads((PACK_PAGES / f"{unit_id}.json").read_text(encoding="utf-8"))
    return {
        "resource_id": "requests",
        "unit_id": unit_id,
        "locator": page["locator"],
        "captured_unit_sha256": page["provenance"]["content_sha256"],
        "uri": f"agentic-anything://requests/units/{unit_id}",
    }


def reviewed_claims(submission: dict[str, Any], read_units: set[str]) -> list[dict[str, Any]]:
    """Rebuild final claims from raw accepted claims, never from reviewed run.json."""
    claims: list[dict[str, Any]] = []
    counts = {"advanced_removed": 0, "exception_tightened": 0, "quickstart_tightened": 0}
    for raw_claim in submission.get("claims") or []:
        resource_id = raw_claim.get("resource_id")
        unit_id = str(raw_claim.get("unit_id") or "")
        text = str(raw_claim.get("claim") or "").strip()
        if resource_id != "requests" or unit_id not in read_units:
            raise RuntimeError(f"raw accepted claim cites an unread unit: {resource_id}/{unit_id}")
        if unit_id == ADVANCED_UNIT:
            if text != "User docs describe Session and max_redirects attribute":
                raise RuntimeError("unexpected advanced.rst claim text in raw accepted submission")
            counts["advanced_removed"] += 1
            continue
        if unit_id == EXCEPTIONS_UNIT:
            if text != "TooManyRedirects exception raised on exceeding redirects":
                raise RuntimeError("unexpected exceptions.py claim text in raw accepted submission")
            text = "TooManyRedirects is defined as a RequestException subtype"
            counts["exception_tightened"] += 1
        elif unit_id == QUICKSTART_UNIT:
            if text != "User docs describe redirect behavior and history":
                raise RuntimeError("unexpected quickstart claim text in raw accepted submission")
            text = (
                "Quickstart states that exceeding the configured maximum raises "
                "TooManyRedirects; it gives no numeric default"
            )
            counts["quickstart_tightened"] += 1
        claims.append({"claim_id": "", "text": text, "support": unit_support(unit_id)})

    if counts != {"advanced_removed": 1, "exception_tightened": 1, "quickstart_tightened": 1}:
        raise RuntimeError(f"raw claim correction assumptions changed: {counts}")
    for index, claim in enumerate(claims, 1):
        claim["claim_id"] = f"claim-{index:02d}"
    if len({claim["text"] for claim in claims}) != len(claims):
        raise RuntimeError("reviewed structured claims contain duplicate wording")
    return claims


def tool_record(name: str, arguments: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "call_id": f"offline-review-{name}",
        "arguments": arguments,
        "duration_ms": 0,
        "result_sha256": digest_bytes(canonical(result)),
        "result_excerpt": json.dumps(result, ensure_ascii=False),
    }


def main() -> int:
    run = portable(json.loads(RUN_PATH.read_text(encoding="utf-8")))
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    accepted_call_id, submission = accepted_submission(raw)
    raw_draft = str(submission.get("artifact_markdown") or "")
    if not raw_draft:
        raise RuntimeError("accepted submit_deliverable has no artifact_markdown")

    model_calls = recorded_model_tool_calls(raw)
    if len(model_calls) != 19:
        raise RuntimeError(f"expected 19 recorded model tool calls; found {len(model_calls)}")
    original_steps = sorted(
        (step for step in run["steps"] if int(step.get("seq", 0)) <= len(model_calls)),
        key=lambda step: step["seq"],
    )
    if [step["seq"] for step in original_steps] != list(range(1, 20)):
        raise RuntimeError("run.json does not preserve recorded public steps 1–19")
    if [
        (step["tool"]["call_id"], step["tool"]["name"], step["tool"]["arguments"])
        for step in original_steps
    ] != model_calls:
        raise RuntimeError("run.json steps 1–19 do not match raw model tool-call order")
    for step in original_steps:
        step["execution_origin"] = "recorded-model-tool-loop"
        step.pop("trace_annotation", None)

    lineage = quickstart_lineage(raw)
    gate_step = next(
        step for step in original_steps
        if step["tool"]["call_id"] == lineage["gate_submit_call_id"]
    )
    quickstart_step = next(
        step for step in original_steps
        if step["tool"]["name"] == "read_unit"
        and step["tool"]["arguments"].get("unit_id") == QUICKSTART_UNIT
    )
    lineage.update({"gate_rejection_step": gate_step["seq"], "first_read_step": quickstart_step["seq"]})
    quickstart_step["trace_annotation"] = {
        "kind": "evidence-gate-directed-read",
        "search_discovered": False,
        "required_by_step": gate_step["seq"],
    }

    # Prove the semantic correction against the actual captured units.
    advanced = json.loads((PACK_PAGES / f"{ADVANCED_UNIT}.json").read_text(encoding="utf-8"))
    quickstart = json.loads((PACK_PAGES / f"{QUICKSTART_UNIT}.json").read_text(encoding="utf-8"))
    advanced_text = "\n".join(item.get("text", "") for item in advanced.get("content", []))
    quickstart_text = "\n".join(item.get("text", "") for item in quickstart.get("content", []))
    if "max_redirects" in advanced_text:
        raise RuntimeError("semantic review assumption changed: advanced.rst now contains max_redirects")
    if "exceeds the configured number of maximum redirections" not in quickstart_text:
        raise RuntimeError("semantic review anchor missing from quickstart.rst")

    corrected_artifact, operations = correct_draft(raw_draft)
    if "advanced.rst" in corrected_artifact or "max_redirects attribute" in corrected_artifact:
        raise RuntimeError("deterministically corrected artifact retains unsupported docs text")
    if "does not explicitly state the numeric default" not in corrected_artifact:
        raise RuntimeError("corrected artifact does not state the documentation boundary")
    if "TooManyRedirects is defined as a RequestException subtype" not in corrected_artifact:
        raise RuntimeError("corrected artifact does not separate exception type from raise site")

    # These are outputs only.  ARTIFACT_PATH is deliberately never read as a
    # review input.
    DRAFT_PATH.write_text(raw_draft, encoding="utf-8")
    ARTIFACT_PATH.write_text(corrected_artifact, encoding="utf-8")

    read_units = {
        step["tool"]["arguments"]["unit_id"]
        for step in original_steps
        if step["tool"]["name"] == "read_unit" and step["status"] == "passed"
    }
    claims = reviewed_claims(submission, read_units)
    transformation = {
        "transform_id": TRANSFORM_ID,
        "input_sha256": digest_text(raw_draft),
        "output_sha256": digest_text(corrected_artifact),
        "operations": operations,
        "terminal_newline": "normalized to exactly one LF",
    }
    audit_result = {
        "accepted": False,
        "unsupported_claim": "docs/user/advanced.rst documents max_redirects",
        "source_draft_sha256": digest_text(raw_draft),
        "evidence": {
            "advanced_contains_max_redirects": False,
            "quickstart_documents_configured_maximum_exception": True,
        },
        "action": "apply the checked exact-once semantic transform",
        "transform_id": TRANSFORM_ID,
    }
    publish_result = {
        "accepted": True,
        "artifact": ARTIFACT_PATH.name,
        "source_draft": DRAFT_PATH.name,
        "source_draft_sha256": digest_file(DRAFT_PATH),
        "artifact_sha256": digest_file(ARTIFACT_PATH),
        "unsupported_claims_remaining": 0,
    }
    review_steps = [
        {
            "seq": 20,
            "phase": "verify",
            "status": "rejected",
            "execution_origin": "deterministic-offline-review",
            "label": "Offline semantic audit rejects an unsupported docs claim",
            "public_action_note": (
                "Deterministic offline step—not a model call. Audit the raw accepted draft "
                "against the two captured documentation units."
            ),
            "tool": tool_record(
                "semantic_claim_audit",
                {
                    "source": f"{RAW_PATH.name}#{accepted_call_id}",
                    "claim": "docs/user/advanced.rst documents max_redirects",
                    "unit_id": ADVANCED_UNIT,
                },
                audit_result,
            ),
            "observation": (
                "The recorded model draft overstates the captured documentation: "
                "advanced.rst never mentions max_redirects."
            ),
            "selected_unit_ids": [ADVANCED_UNIT, QUICKSTART_UNIT],
        },
        {
            "seq": 21,
            "phase": "deliver",
            "status": "passed",
            "execution_origin": "deterministic-offline-review",
            "label": "Offline reviewer deterministically publishes the corrected brief",
            "public_action_note": (
                "Deterministic offline step—not a model call. Apply five asserted exact-once "
                "replacements to the preserved raw model draft."
            ),
            "tool": tool_record(
                "publish_reviewed_artifact",
                {
                    "source": DRAFT_PATH.name,
                    "transform_id": TRANSFORM_ID,
                    "output": ARTIFACT_PATH.name,
                },
                publish_result,
            ),
            "observation": (
                "The final artifact is regenerated from the raw accepted draft; it states "
                "only quickstart's exact contract and separates the raise site from the exception type."
            ),
            "selected_unit_ids": [SESSIONS_UNIT, EXCEPTIONS_UNIT, QUICKSTART_UNIT],
        },
    ]
    run["steps"] = original_steps + review_steps

    run["artifact"].update({
        "name": ARTIFACT_PATH.name,
        "sha256": digest_file(ARTIFACT_PATH),
        "title": str(submission.get("title") or ""),
        "summary": str(submission.get("summary") or ""),
        "content": corrected_artifact.rstrip("\n"),
        "limitations": list(submission.get("limitations") or []),
        "review_status": "recorded model draft + deterministic offline semantic review",
        "source_draft": DRAFT_PATH.name,
        "source_draft_sha256": digest_file(DRAFT_PATH),
        "transform_id": TRANSFORM_ID,
    })
    run["claims"] = claims

    checks = [item for item in run["checks"] if item["id"] not in {
        "claim_citations_were_read", "artifact_written", "evidence_gate_accepted",
        "structural_evidence_gate", "semantic_claim_audit", "reviewed_artifact_written",
    }]
    checks.extend([
        {
            "id": "claim_citations_were_read",
            "passed": True,
            "detail": (
                f"{len(claims)} final claims; every unit was read; quickstart was "
                "gate-directed rather than search-discovered"
            ),
        },
        {
            "id": "structural_evidence_gate",
            "passed": True,
            "detail": "recorded model draft covered all required code, test, exception, and docs roles",
        },
        {
            "id": "semantic_claim_audit",
            "passed": True,
            "detail": (
                f"accepted raw draft {digest_file(DRAFT_PATH)} regenerated with "
                f"{len(operations)} asserted exact-once replacements"
            ),
        },
        {
            "id": "reviewed_artifact_written",
            "passed": True,
            "detail": f"{ARTIFACT_PATH.name} · sha256 {digest_file(ARTIFACT_PATH)}",
        },
    ])
    run["checks"] = checks

    recording = run["recording"]
    recording.pop("tool_calls", None)
    recording["model_tool_calls"] = len(model_calls)
    recording["recorded_model_mcp_steps"] = len(original_steps)
    recording["offline_review_steps"] = len(review_steps)
    recording["visible_timeline_steps"] = len(run["steps"])
    raw_scope = (
        "raw-transcript.json contains recorded model messages/tool calls and MCP JSON-RPC "
        "for steps 1–19 only; deterministic offline review/publish steps 20–21 are in run.json."
    )
    run["timeline"] = {
        "visible_steps": 21,
        "segments": [
            {
                "id": "recorded-model-mcp",
                "first_step": 1,
                "last_step": 19,
                "step_count": 19,
                "source": RAW_PATH.name,
            },
            {
                "id": "deterministic-offline-review",
                "first_step": 20,
                "last_step": 21,
                "step_count": 2,
                "source": "review_recorded_llm_run.py",
            },
        ],
        "raw_transcript_scope": raw_scope,
    }
    run["evidence_lineage"] = {"quickstart": lineage}
    run["verification"].update({
        "passed": all(item["passed"] for item in checks),
        "passed_count": sum(item["passed"] for item in checks),
        "total_count": len(checks),
        "raw_transcript_sha256": digest_file(RAW_PATH),
        "raw_transcript_scope": raw_scope,
        "replay_note": (
            "Steps 1–19 replay the recorded model/MCP trace. Steps 20–21 are deterministic "
            "offline operations that re-extract the accepted model draft and regenerate the artifact."
        ),
    })
    run["draft_review"] = {
        "raw_model_draft_preserved": True,
        "source_of_truth": "last accepted submit_deliverable artifact_markdown in raw-transcript.json",
        "accepted_submit_call_id": accepted_call_id,
        "source_draft": {
            "name": DRAFT_PATH.name,
            "sha256": digest_file(DRAFT_PATH),
            "bytes": len(raw_draft.encode("utf-8")),
        },
        "deterministic_transform": transformation,
        "rejected_claim": audit_result["unsupported_claim"],
        "final_artifact_is_reviewed": True,
    }

    text = json.dumps(run, ensure_ascii=False, indent=2) + "\n"
    publishable = text + RAW_PATH.read_text(encoding="utf-8") + raw_draft + corrected_artifact
    forbidden = (str(ROOT), "sk-or-v1-")
    if any(marker in publishable for marker in forbidden):
        raise RuntimeError("publishable recording contains a local path or credential marker")
    RUN_PATH.write_text(text, encoding="utf-8")
    print(
        f"reviewed {run['run_id']}: 19 recorded + 2 offline steps, "
        f"{len(claims)} claims, {run['verification']['passed_count']}/"
        f"{run['verification']['total_count']} checks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
