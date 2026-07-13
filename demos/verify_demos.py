#!/usr/bin/env python3
"""Verify authentic packs, long-horizon recordings, and publishable demo UI."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
SOURCES = DEMO / "sources"
RUNS = DEMO / "runs"
EXPECTED = {"requests", "alice", "secrets", "gistemp", "fair-paper"}
EXPECTED_PHRASES = {
    "requests": "DEFAULT_REDIRECT_LIMIT",
    "alice": "slightest idea",
    "secrets": "32 bytes (256 bits)",
    "gistemp": "2024 | 1.25",
    "fair-paper": "identify the type of object",
}
FORBIDDEN_ARTIFACT_MARKERS = ("/newcpfs/", "sk-or-v1-")


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


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_sources_and_packs() -> tuple[dict, dict[str, dict]]:
    source_manifest = load(SOURCES / "real-sources.json")
    declared = source_manifest["sources"]
    check(set(declared) == EXPECTED, "source manifest declares exactly five real resources")
    for demo_id, meta in declared.items():
        source = SOURCES / meta["snapshot_file"]
        check(source.is_file(), f"{demo_id} source snapshot is checked in")
        check(sha256_file(source) == meta["sha256"], f"{demo_id} source SHA-256 matches publisher snapshot")
        check(meta["origin_url"].startswith("https://"), f"{demo_id} has a publisher URL")
        check(bool(meta["license"] and meta["license_url"]), f"{demo_id} has license provenance")

    payload = load(DEMO / "results" / "showcase.json")
    demos = {item["id"]: item for item in payload["demos"]}
    check(set(demos) == EXPECTED, "all five authentic demo resources are present")
    check(payload["summary"]["publishers"] == 5, "showcase spans five named publishers")
    check(payload["summary"]["resource_types"] == 5, "showcase spans five native resource types")
    check(payload["summary"]["units"] == 93, "showcase contains ninety-three real evidence units")
    check(payload["synthetic_source_lines"] == 0, "showcase declares zero synthetic source lines")
    check(all(payload["assertions"].values()), "all pack showcase quality assertions pass")
    check(payload["model_calls"] == 0, "pack build itself uses zero model calls")

    for demo_id, item in demos.items():
        evidence = " ".join(block["text"] for block in item["query_result"]["evidence_blocks"])
        check(EXPECTED_PHRASES[demo_id].casefold() in evidence.casefold(),
              f"{demo_id} checked answer is supported by visible evidence")
        check(item["source"]["sha256"] == declared[demo_id]["sha256"] and item["source"]["verified"],
              f"{demo_id} result retains source provenance")
        pack = DEMO / "packs" / demo_id
        site = load(pack / "site.json")
        check("127.0.0.1:" not in site.get("seed_url", ""), f"{demo_id} public locator is not the local capture server")
        for relative in ("agent-pack.json", "agent-interface.json", "AGENT.md", "skills/SKILL.md"):
            check((pack / relative).is_file(), f"{demo_id} contains {relative}")
        cli = next((pack / "cli").glob("*_cli.py"))
        proc = subprocess.run([sys.executable, str(cli), "info"], text=True, capture_output=True, timeout=30)
        check(proc.returncode == 0 and f"site_id: {demo_id}" in proc.stdout, f"{demo_id} generated CLI runs")

    gistemp_site = load(DEMO / "packs/gistemp/site.json")
    gistemp_ids = {item["page_id"] for item in gistemp_site["pages"]}
    check("nasa-gistemp-global__003__nasa-gistemp-global-csv-rows-101-147" in gistemp_ids,
          "GISTEMP pack uses the corrected 147-row boundary")
    overview = load(DEMO / "packs/gistemp/pages/nasa-gistemp-global__001__nasa-gistemp-global-csv-overview.json")
    overview_text = "\n".join(item["text"] for item in overview["content"])
    check("147 data rows, 19 columns" in overview_text and "Preamble:" in overview_text,
          "GISTEMP overview preserves its title preamble and real 19-column schema")
    return payload, declared


def verify_deterministic_run(entry: dict) -> None:
    run_id = entry["run_id"]
    directory = RUNS / run_id
    for meta in entry["files"].values():
        path = RUNS / meta["path"]
        check(path.is_file() and sha256_file(path) == meta["sha256"], f"{run_id} indexed file hash matches: {path.name}")
    run = load(directory / "run.json")
    verification = load(directory / "verification.json")
    check(run["mode"] == "deterministic-evidence-agent" and run["model_calls"] == 0,
          f"{run_id} is explicitly a zero-model deterministic agent")
    check(len(run["steps"]) >= 14 and run["summary"]["search_calls"] >= 5 and run["summary"]["read_calls"] >= 4,
          f"{run_id} has a genuinely multi-step search/read horizon")
    check(verification["passed"] and all(item["passed"] for item in verification["assertions"]),
          f"{run_id} offline assertions all pass")
    read_steps = {
        (step["tool_input"]["resource_id"], step["tool_input"]["unit_id"]): step["step"]
        for step in run["steps"] if step["tool"] == "read_unit"
    }
    check(all(
        (item["resource_id"], item["unit_id"]) in read_steps
        and read_steps[(item["resource_id"], item["unit_id"])] == item["read_step"]
        for item in run["citations"]
    ), f"{run_id} cites only units read earlier in the run")
    check(sha256_file(directory / "artifact.md") == verification["artifact_sha256"],
          f"{run_id} final artifact hash matches verification")


def verify_llm_run(entry: dict, declared: dict[str, dict]) -> None:
    directory = RUNS / entry["run_id"]
    run = load(directory / "run.json")
    raw_path = directory / run["verification"]["raw_transcript"]
    artifact_path = directory / run["artifact"]["name"]
    check(run["mode"] == "real-llm-tool-loop+mcp-stdio", "recorded run is explicitly a real LLM + stdio MCP loop")
    check(run["recording"]["model"] == "openai/gpt-4.1-mini" and run["recording"]["model_calls"] == 10,
          "recorded run retains exact model and turn count")
    check(run["recording"]["model_tool_calls"] == 19 and len(run["steps"]) == 21,
          "recorded run contains nineteen model tool calls plus two offline review steps")
    rejected = [step for step in run["steps"] if step["status"] == "rejected"]
    check(len(rejected) == 2 and {step["phase"] for step in rejected} == {"deliver", "verify"},
          "recording visibly preserves both evidence-gate and semantic-review rejections")
    check(run["verification"]["passed"] and all(item["passed"] for item in run["checks"]),
          "recorded LLM run passes every publishability check")
    check(sha256_file(raw_path) == run["verification"]["raw_transcript_sha256"],
          "raw model/MCP transcript hash matches")
    check(sha256_file(artifact_path) == run["artifact"]["sha256"], "reviewed model artifact hash matches")
    check(run["artifact"]["content"] == artifact_path.read_text(encoding="utf-8").rstrip("\n"),
          "HTML payload and checked-in reviewed artifact are identical")
    check(run["packs"][0]["snapshot_sha256"] == declared["requests"]["sha256"],
          "model recording is tied to the authentic Requests release snapshot")

    read_units = {
        step["tool"]["arguments"]["unit_id"]
        for step in run["steps"]
        if step["tool"]["name"] == "read_unit" and step["status"] == "passed"
    }
    final_units = {claim["support"]["unit_id"] for claim in run["claims"]}
    check(final_units.issubset(read_units), "every final LLM claim cites a unit the model actually read")
    for claim in run["claims"]:
        page = load(DEMO / "packs/requests/pages" / f"{claim['support']['unit_id']}.json")
        check(page["provenance"]["content_sha256"] == claim["support"]["captured_unit_sha256"],
              f"LLM claim unit hash matches pack: {claim['support']['unit_id']}")
    raw_text = raw_path.read_text(encoding="utf-8")
    final_text = artifact_path.read_text(encoding="utf-8")
    check("User docs describe Session and max_redirects attribute" in raw_text,
          "raw transcript preserves the model's unsupported draft claim for audit")
    check("advanced.rst" not in final_text and "does not explicitly state the numeric default" in final_text,
          "semantic reviewer removes the unsupported claim and states the evidence boundary")


def verify_runs(declared: dict[str, dict]) -> None:
    index = load(RUNS / "index.json")
    entries = {item["run_id"]: item for item in index["runs"]}
    expected_runs = {"requests-redirect-impact-llm", "requests-redirect-impact", "gistemp-fair-audit"}
    check(set(entries) == expected_runs, "run index contains one real model run and two deterministic long runs")
    check(index["summary"] == {
        "all_passed": True,
        "assertions_passed": 52,
        "assertions_total": 52,
        "run_count": 3,
        "runs_passed": 3,
    }, "all fifty-two long-run checks pass")
    check(index["model_calls"] == 10, "index separates ten recorded model calls from zero-call rebuilds")
    verify_llm_run(entries["requests-redirect-impact-llm"], declared)
    verify_deterministic_run(entries["requests-redirect-impact"])
    verify_deterministic_run(entries["gistemp-fair-audit"])


def verify_publishable_html() -> None:
    publishable = [
        path for path in DEMO.rglob("*")
        if path.is_file()
        and path.suffix in {".json", ".md", ".html", ".txt", ".jsonl"}
        and path.name not in {"real-sources.json"}
    ]
    leaks: list[str] = []
    for path in publishable:
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_ARTIFACT_MARKERS:
            if marker in text:
                leaks.append(f"{path.relative_to(ROOT)} contains {marker!r}")
    check(not leaks, "published artifacts exclude local paths and credential markers")

    html = (DEMO / "index.html").read_text(encoding="utf-8")
    required_story = (
        "Watch the work, not a one-line answer.",
        "runs/requests-redirect-impact-llm/run.json",
        "runs/gistemp-fair-audit/run.json",
        "Exact tool input",
        "Recorded output",
        "Claim → evidence ledger",
        "The run ends with",
        "Real inputs, pinned",
        "Boundary of this demo",
        "The page is a replay.",
    )
    check(all(marker in html for marker in required_story),
          "HTML leads with long work, exact tool traces, artifacts, evidence, and explicit replay limits")


def main() -> int:
    _, declared = verify_sources_and_packs()
    verify_runs(declared)
    verify_publishable_html()
    print("\nLong-horizon authentic demo verification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
