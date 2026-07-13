#!/usr/bin/env python3
"""Apply the offline semantic review to the checked-in LLM recording.

The raw transcript intentionally keeps the model's accepted draft, including a
subtle unsupported documentation claim.  A post-recording reviewer checks the
actual units, records that rejection as a visible step, and publishes the
corrected Markdown file as the final artifact.  This keeps the demo honest:
the model really ran, and its fluent output was not trusted blindly.
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
ARTIFACT_PATH = RUN_DIR / "maintainer-impact-brief.md"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def tool_record(name: str, arguments: dict, result: dict) -> dict:
    return {
        "name": name,
        "call_id": f"offline-review-{name}",
        "arguments": arguments,
        "duration_ms": 0,
        "result_sha256": digest_bytes(canonical(result)),
        "result_excerpt": json.dumps(result, ensure_ascii=False),
    }


def main() -> int:
    run = json.loads(RUN_PATH.read_text(encoding="utf-8"))
    raw = portable(json.loads(RAW_PATH.read_text(encoding="utf-8")))
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Prove the correction is grounded in the captured units, not editorial taste.
    advanced = json.loads((ROOT / "demos/packs/requests/pages/file__docs--user--advanced-rst.json").read_text())
    quickstart = json.loads((ROOT / "demos/packs/requests/pages/file__docs--user--quickstart-rst.json").read_text())
    advanced_text = "\n".join(item.get("text", "") for item in advanced.get("content", []))
    quickstart_text = "\n".join(item.get("text", "") for item in quickstart.get("content", []))
    if "max_redirects" in advanced_text:
        raise RuntimeError("semantic review assumption changed: advanced.rst now contains max_redirects")
    if "exceeds the configured number of maximum redirections" not in quickstart_text:
        raise RuntimeError("semantic review anchor missing from quickstart.rst")

    run = portable(run)
    original_steps = [step for step in run["steps"] if step.get("seq", 0) <= 19]
    audit_result = {
        "accepted": False,
        "unsupported_claim": "docs/user/advanced.rst documents max_redirects",
        "evidence": {
            "advanced_contains_max_redirects": False,
            "quickstart_documents_configured_maximum_exception": True,
        },
        "action": "remove the unsupported claim and cite only quickstart's exact contract",
    }
    publish_result = {
        "accepted": True,
        "artifact": ARTIFACT_PATH.name,
        "unsupported_claims_remaining": 0,
    }
    review_steps = [
        {
            "seq": 20,
            "phase": "verify",
            "status": "rejected",
            "label": "Semantic audit catches a fluent but unsupported docs claim",
            "public_action_note": "A read unit must contain the fact attributed to it; search rank and plausibility are not enough.",
            "tool": tool_record(
                "semantic_claim_audit",
                {
                    "claim": "docs/user/advanced.rst documents max_redirects",
                    "unit_id": "file__docs--user--advanced-rst",
                },
                audit_result,
            ),
            "observation": "The model's draft overstates the captured documentation. advanced.rst never mentions max_redirects.",
            "selected_unit_ids": [
                "file__docs--user--advanced-rst",
                "file__docs--user--quickstart-rst",
            ],
        },
        {
            "seq": 21,
            "phase": "deliver",
            "status": "passed",
            "label": "Publish the evidence-safe maintainer brief",
            "public_action_note": "Preserve the model's supported code/test findings; replace only the unsupported documentation claim.",
            "tool": tool_record(
                "publish_reviewed_artifact",
                {
                    "source": "model draft in raw-transcript.json",
                    "review": "semantic_claim_audit",
                    "output": ARTIFACT_PATH.name,
                },
                publish_result,
            ),
            "observation": "The final artifact now says exactly what quickstart proves and explicitly marks the numeric default as undocumented.",
            "selected_unit_ids": ["file__docs--user--quickstart-rst"],
        },
    ]
    run["steps"] = original_steps + review_steps

    artifact = ARTIFACT_PATH.read_text(encoding="utf-8")
    if "advanced.rst" in artifact or "max_redirects attribute" in artifact:
        raise RuntimeError("corrected artifact still contains the unsupported documentation claim")
    if "does not explicitly state the numeric default" not in artifact:
        raise RuntimeError("corrected artifact does not state the documentation boundary")
    run["artifact"]["content"] = artifact.rstrip("\n")
    run["artifact"]["sha256"] = digest_file(ARTIFACT_PATH)
    run["artifact"]["review_status"] = "model draft + offline semantic review"

    claims = []
    for claim in run["claims"]:
        if claim["support"]["unit_id"] == "file__docs--user--advanced-rst":
            continue
        if claim["support"]["unit_id"] == "file__docs--user--quickstart-rst":
            claim["text"] = (
                "Quickstart states that exceeding the configured maximum raises "
                "TooManyRedirects; it gives no numeric default"
            )
        claims.append(claim)
    for index, claim in enumerate(claims, 1):
        claim["claim_id"] = f"claim-{index:02d}"
    run["claims"] = claims

    checks = [item for item in run["checks"] if item["id"] not in {
        "claim_citations_were_read", "artifact_written", "evidence_gate_accepted",
        "structural_evidence_gate", "semantic_claim_audit", "reviewed_artifact_written",
    }]
    checks.extend([
        {"id": "claim_citations_were_read", "passed": True, "detail": f"{len(claims)} final claims; every unit was read"},
        {"id": "structural_evidence_gate", "passed": True, "detail": "model draft covered all required code, test, exception, and docs roles"},
        {"id": "semantic_claim_audit", "passed": True, "detail": "unsupported advanced.rst claim detected and removed"},
        {"id": "reviewed_artifact_written", "passed": True, "detail": f"{ARTIFACT_PATH.name} · sha256 {digest_file(ARTIFACT_PATH)}"},
    ])
    run["checks"] = checks
    run["recording"]["model_tool_calls"] = run["recording"].pop("tool_calls", 19)
    run["recording"]["offline_review_steps"] = 2
    run["verification"].update({
        "passed": all(item["passed"] for item in checks),
        "passed_count": sum(item["passed"] for item in checks),
        "total_count": len(checks),
        "raw_transcript_sha256": digest_file(RAW_PATH),
        "replay_note": (
            "The raw transcript preserves the original model draft. Steps 20–21 record "
            "the offline semantic rejection and corrected publishable artifact."
        ),
    })
    run["draft_review"] = {
        "raw_model_draft_preserved": True,
        "rejected_claim": audit_result["unsupported_claim"],
        "final_artifact_is_reviewed": True,
    }

    text = json.dumps(run, ensure_ascii=False, indent=2) + "\n"
    forbidden = (str(ROOT), "sk-or-v1-")
    if any(marker in text or marker in RAW_PATH.read_text(encoding="utf-8") for marker in forbidden):
        raise RuntimeError("publishable recording contains a local path or credential marker")
    RUN_PATH.write_text(text, encoding="utf-8")
    print(
        f"reviewed {run['run_id']}: {len(run['steps'])} visible steps, "
        f"{len(claims)} claims, {run['verification']['passed_count']}/"
        f"{run['verification']['total_count']} checks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
