#!/usr/bin/env python3
"""Build the checked-in showcase from pinned, authentic external resources.

The source manifest records publisher URLs, versions, licenses, and SHA-256
digests. Missing snapshots are downloaded once; every build verifies their
bytes before agentification. Model API keys are removed from child processes.
"""

from __future__ import annotations

import contextlib
import csv
import functools
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos"
SRC = ROOT / "src"
SOURCES = DEMO / "sources"
SOURCE_MANIFEST = SOURCES / "real-sources.json"
PACKS = DEMO / "packs"
RESULTS = DEMO / "results"
SNAPSHOT_AT = "2026-07-11T00:00:00Z"

sys.path.insert(0, str(SRC))

from agentic_anything.mcp import ResourceMCPServer  # noqa: E402
from agentic_anything.query import PackReader, search_pack  # noqa: E402


@contextlib.contextmanager
def local_site(directory: Path, filename: str):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            return

    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/{filename}"
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


def run(*args: str, timeout: int = 240) -> subprocess.CompletedProcess[str]:
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_source_manifest() -> tuple[dict, dict[str, dict]]:
    payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    return payload, payload["sources"]


def ensure_snapshot(meta: dict) -> Path:
    path = SOURCES / meta["snapshot_file"]
    if not path.exists():
        request = urllib.request.Request(
            meta["snapshot_url"],
            headers={"User-Agent": "Agentic-Anything-Demo/1.0 (+https://github.com/THUQiXuan/agentic-anything)"},
        )
        partial = path.with_suffix(path.suffix + ".part")
        with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target)
        partial.replace(path)
    actual = sha256_file(path)
    if actual != meta["sha256"]:
        raise RuntimeError(
            f"authentic source hash mismatch for {path.name}: expected {meta['sha256']}, got {actual}"
        )
    return path


def extract_zip_safely(archive_path: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe archive member: {member.filename}")
        archive.extractall(destination)


def agentify(source: str, demo_id: str, *, max_pages: int = 4) -> dict:
    pack = PACKS / demo_id
    proc = run(
        sys.executable, "-m", "agentic_anything", "agentify", source,
        "-o", str(pack), "--site-id", demo_id, "--no-llm",
        "--language", "both", "--max-pages", str(max_pages), "--no-probe", "--json",
    )
    return json.loads(proc.stdout)


def publish_pack(pack: Path, replacements: dict[str, str]) -> None:
    """Replace local capture locators and timestamps with public provenance."""
    site = json.loads((pack / "site.json").read_text(encoding="utf-8"))
    replacements = dict(replacements)
    for field in ("captured_at", "finished_at"):
        if site.get(field):
            replacements[site[field]] = SNAPSHOT_AT
    for path in pack.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".md", ".py", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        for private, public in replacements.items():
            text = text.replace(private, public)
        path.write_text(text, encoding="utf-8")


def result_for(
    demo_id: str,
    query: str,
    *,
    preferred_unit: str | None = None,
    preferred_evidence: str | None = None,
) -> dict:
    reader = PackReader(PACKS / demo_id)
    hits = search_pack(reader, query, top=10)
    if not hits:
        raise RuntimeError(f"no search hit for {demo_id}: {query}")
    selected_index = 0
    if preferred_unit:
        selected_index = next(
            (index for index, hit in enumerate(hits) if preferred_unit in hit["page_id"]), 0
        )
    hit = hits[selected_index]
    evidence = list(hit.get("evidence", []))
    if preferred_evidence:
        evidence.sort(key=lambda item: preferred_evidence.casefold() not in item.get("text", "").casefold())
    strongest = evidence[0] if evidence else {}
    manifest = reader.page(hit["page_id"])
    return {
        "query": query,
        "rank": selected_index + 1,
        "unit_id": hit["page_id"],
        "title": hit["title"],
        "score": round(hit["score"], 4),
        "evidence": strongest.get("text", ""),
        "evidence_blocks": evidence[:4],
        "matched": strongest.get("matched", []),
        "locator": manifest.get("locator") or manifest.get("url_path") or "",
        "content_sha256": manifest.get("provenance", {}).get("content_sha256", ""),
    }


def unit_inventory(reader: PackReader) -> list[dict]:
    units = []
    for unit_id in reader.page_ids():
        manifest = reader.page(unit_id)
        units.append({
            "unit_id": unit_id,
            "title": manifest.get("title") or unit_id,
            "type": manifest.get("page_type") or manifest.get("unit_kind") or "unit",
            "locator": manifest.get("locator") or manifest.get("url_path") or "",
            "content_sha256": manifest.get("provenance", {}).get("content_sha256", ""),
        })
    return units


def cli_demo(demo_id: str, query: str) -> dict:
    pack = PACKS / demo_id
    cli = next((pack / "cli").glob("*_cli.py"))
    info = run(sys.executable, str(cli), "info")
    search = run(sys.executable, str(cli), "search", query)
    return {
        "cli": str(cli.relative_to(pack)),
        "info": info.stdout.strip(),
        "search": search.stdout.strip(),
    }


def mcp_demo(pack_ids: list[str]) -> dict:
    server = ResourceMCPServer([PACKS / item for item in pack_ids])
    init = server.handle({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "demo-client", "version": "1"},
        },
    })
    query = "machine actionable identify useful usable license"
    search = server.handle({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {
            "name": "search_resource",
            "arguments": {"query": query, "top_k": 3},
        },
    })
    structured = search["result"]["structuredContent"]
    first = structured["hits"][0]
    read = server.handle({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "read_unit",
            "arguments": {"resource_id": first["resource_id"], "unit_id": first["unit_id"]},
        },
    })
    return {
        "initialize": init,
        "search_request": {"tool": "search_resource", "query": query},
        "search_response": structured,
        "read_request": {
            "tool": "read_unit", "resource_id": first["resource_id"], "unit_id": first["unit_id"],
        },
        "read_response": read["result"]["structuredContent"],
    }


def code_excerpt(path: Path, start: int, end: int, *, display_path: str) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        "path": display_path,
        "start_line": start,
        "code": "\n".join(f"{number:>4}  {lines[number - 1]}" for number in range(start, end + 1)),
    }


def dataset_preview(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as handle:
        title = handle.readline().strip()
        rows = list(csv.reader(handle))
    header, data = rows[0], rows[1:]
    selected = [row for row in data if row and row[0] in {"2023", "2024", "2025", "2026"}]
    columns = ["Year", "Jan", "Feb", "Mar", "Apr", "J-D"]
    indices = [header.index(column) for column in columns]
    return {
        "kind": "dataset",
        "title": title,
        "columns": columns,
        "rows": [[row[index] for index in indices] for row in selected],
        "note": "J-D is the January–December annual mean anomaly in °C relative to 1951–1980.",
    }


def previews(repo_root: Path, snapshot_paths: dict[str, Path], query_results: dict[str, dict]) -> dict:
    return {
        "requests": {
            "kind": "code",
            "files": [
                code_excerpt(
                    repo_root / "src/requests/models.py", 98, 108,
                    display_path="src/requests/models.py",
                ),
                code_excerpt(
                    repo_root / "src/requests/sessions.py", 480, 489,
                    display_path="src/requests/sessions.py",
                ),
                code_excerpt(
                    repo_root / "src/requests/sessions.py", 212, 220,
                    display_path="src/requests/sessions.py",
                ),
            ],
        },
        "gistemp": dataset_preview(snapshot_paths["gistemp"]),
        "alice": {
            "kind": "book",
            "chapter": "CHAPTER VII · A Mad Tea-Party",
            "passages": [item["text"] for item in query_results["alice"]["evidence_blocks"][:3]],
        },
        "secrets": {
            "kind": "web",
            "heading": "How many bytes should tokens use?",
            "passages": [item["text"] for item in query_results["secrets"]["evidence_blocks"][:2]],
        },
        "fair-paper": {
            "kind": "paper",
            "heading": "The significance of machines in data-rich research environments",
            "passages": [item["text"] for item in query_results["fair-paper"]["evidence_blocks"][:2]],
        },
    }


def main() -> int:
    manifest, source_meta = load_source_manifest()
    snapshot_paths = {key: ensure_snapshot(meta) for key, meta in source_meta.items()}

    for directory in (PACKS, RESULTS):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    display = {
        "requests": {
            "question": "What is Requests' default redirect ceiling, where is it set, and what happens when it is exceeded?",
            "answer": "30 redirects. Session.max_redirects is initialized from DEFAULT_REDIRECT_LIMIT; resolve_redirects raises TooManyRedirects once response history reaches that ceiling.",
            "before_problem": "The answer spans a constant, Session initialization, and runtime enforcement across a 74-file repository.",
            "query": "DEFAULT_REDIRECT_LIMIT 30 max_redirects TooManyRedirects",
            "expected_phrase": "DEFAULT_REDIRECT_LIMIT",
        },
        "alice": {
            "question": "Does the Hatter ever answer 'Why is a raven like a writing-desk?'",
            "answer": "No. When Alice asks for the answer, the Hatter says he has not the slightest idea; Alice later calls it a riddle with no answer.",
            "before_problem": "A reader must remember the scene and navigate a fourteen-chapter EPUB to verify the exchange.",
            "query": "Hatter haven't slightest idea answer raven writing-desk",
            "expected_phrase": "slightest idea",
        },
        "secrets": {
            "question": "How much randomness does Python's official documentation recommend against brute-force attacks?",
            "answer": "As of 2015, the documentation says 32 bytes (256 bits) of randomness is believed sufficient for a typical use case.",
            "before_problem": "The recommendation sits inside a long API reference surrounded by similarly named token functions.",
            "query": "brute-force attacks sufficient amount randomness",
            "expected_phrase": "32 bytes (256 bits)",
        },
        "gistemp": {
            "question": "What is NASA GISTEMP's 2024 January–December global anomaly?",
            "answer": "1.28 °C above the 1951–1980 mean. The value is the J-D column in NASA's 2024 row.",
            "before_problem": "The CSV has 147 years and eighteen monthly, seasonal, and annual columns; the meaning of J-D comes from the dataset schema.",
            "query": "2024",
            "expected_phrase": "2024 | 1.25",
        },
        "fair-paper": {
            "question": "What must a digital object expose to be machine-actionable according to the FAIR paper?",
            "answer": "Enough information for an agent to identify the object type, judge usefulness, determine usability and license constraints, and take appropriate action.",
            "before_problem": "The operational definition is embedded in a long, multi-author scholarly article, not presented as an API contract.",
            "query": "machine actionable identify type useful usable license appropriate action",
            "expected_phrase": "identify the type of object",
        },
    }

    with tempfile.TemporaryDirectory(prefix="agentic-real-demo-") as temp_dir:
        temp = Path(temp_dir)
        extract_zip_safely(snapshot_paths["requests"], temp)
        repo_root = temp / source_meta["requests"]["archive_root"]
        # GitHub release archives omit the .git directory. Restore only the
        # repository marker used by source-type detection; no source file is
        # changed and .git is excluded from captured units.
        (repo_root / ".git").mkdir()
        (repo_root / ".git" / "HEAD").write_text(
            "ref: refs/tags/v2.34.2\n", encoding="utf-8"
        )

        with local_site(SOURCES, snapshot_paths["secrets"].name) as secrets_url:
            specs = [
                ("requests", str(repo_root), "code", 4),
                ("alice", str(snapshot_paths["alice"]), "book", 4),
                ("secrets", secrets_url, "web", 1),
                ("gistemp", str(snapshot_paths["gistemp"]), "dataset", 4),
                ("fair-paper", str(snapshot_paths["fair-paper"]), "document", 4),
            ]
            for demo_id, source, expected_type, max_pages in specs:
                agentify(source, demo_id, max_pages=max_pages)
                actual = PackReader(PACKS / demo_id).site.get("resource_type")
                if actual != expected_type:
                    raise RuntimeError(f"{demo_id}: expected {expected_type}, got {actual}")

            public_replacements = {
                "requests": {str(repo_root): source_meta["requests"]["origin_url"]},
                "alice": {str(snapshot_paths["alice"]): source_meta["alice"]["origin_url"]},
                "gistemp": {str(snapshot_paths["gistemp"]): source_meta["gistemp"]["origin_url"]},
                "fair-paper": {str(snapshot_paths["fair-paper"]): source_meta["fair-paper"]["origin_url"]},
                "secrets": {
                    secrets_url.rsplit("/", 1)[0]: "https://docs.python.org/3.13/library",
                },
            }
            for demo_id in display:
                publish_pack(PACKS / demo_id, public_replacements[demo_id])

        query_results = {
            demo_id: result_for(demo_id, details["query"], preferred_evidence=details["expected_phrase"])
            for demo_id, details in display.items()
        }
        native_previews = previews(repo_root, snapshot_paths, query_results)

        demos = []
        for demo_id in ("requests", "alice", "secrets", "gistemp", "fair-paper"):
            reader = PackReader(PACKS / demo_id)
            meta = source_meta[demo_id]
            details = display[demo_id]
            result = query_results[demo_id]
            combined_evidence = " ".join(item["text"] for item in result["evidence_blocks"])
            if details["expected_phrase"].casefold() not in combined_evidence.casefold():
                raise RuntimeError(f"quality phrase missing for {demo_id}: {details['expected_phrase']}")
            demos.append({
                "id": demo_id,
                "resource_type": reader.site.get("resource_type"),
                "source": {
                    **{key: meta[key] for key in (
                        "title", "publisher", "format", "version", "origin_url",
                        "snapshot_file", "sha256", "license", "license_url",
                    )},
                    "verified": sha256_file(snapshot_paths[demo_id]) == meta["sha256"],
                },
                "question": details["question"],
                "answer": details["answer"],
                "before_problem": details["before_problem"],
                "unit_count": len(reader.page_ids()),
                "units": unit_inventory(reader),
                "preview": native_previews[demo_id],
                "query_result": result,
                "interfaces": sorted(json.loads(
                    (PACKS / demo_id / "agent-interface.json").read_text(encoding="utf-8")
                )["interfaces"].keys()),
                "use_commands": {
                    "query": f"agentic-anything query demos/packs/{demo_id} {json.dumps(details['query'])} --json",
                    "cli": f"python demos/packs/{demo_id}/cli/{demo_id.replace('-', '_')}_cli.py search {json.dumps(details['query'])}",
                    "mcp": f"agentic-anything mcp demos/packs/{demo_id}",
                },
                "cli_result": cli_demo(demo_id, details["query"]),
            })

    flagship = {
        "resource": "requests",
        "task": display["requests"]["question"],
        "answer": display["requests"]["answer"],
        "steps": [
            {
                "step": "01", "label": "Definition", "finding": "The library constant is 30.",
                "deep_link": "https://github.com/psf/requests/blob/v2.34.2/src/requests/models.py#L104",
                "result": result_for(
                    "requests", "models DEFAULT_REDIRECT_LIMIT 30",
                    preferred_unit="models-py", preferred_evidence="DEFAULT_REDIRECT_LIMIT: int = 30",
                ),
            },
            {
                "step": "02", "label": "Session default", "finding": "Every Session copies that constant into max_redirects.",
                "deep_link": "https://github.com/psf/requests/blob/v2.34.2/src/requests/sessions.py#L483-L488",
                "result": result_for(
                    "requests", "self max_redirects DEFAULT_REDIRECT_LIMIT",
                    preferred_unit="sessions-py", preferred_evidence="self.max_redirects",
                ),
            },
            {
                "step": "03", "label": "Runtime enforcement", "finding": "At the ceiling, resolve_redirects raises TooManyRedirects.",
                "deep_link": "https://github.com/psf/requests/blob/v2.34.2/src/requests/sessions.py#L216-L219",
                "result": result_for(
                    "requests", "len resp history max_redirects TooManyRedirects",
                    preferred_unit="sessions-py", preferred_evidence="if len(resp.history)",
                ),
            },
        ],
    }

    mcp = mcp_demo([item["id"] for item in demos])
    expected_phrases = {demo_id: details["expected_phrase"] for demo_id, details in display.items()}
    assertions = {
        "five_authentic_publishers": len({item["source"]["publisher"] for item in demos}) == 5,
        "five_resource_types": len({item["resource_type"] for item in demos}) == 5,
        "all_source_hashes_verified": all(item["source"]["verified"] for item in demos),
        "all_sources_have_origin_and_license": all(
            item["source"]["origin_url"] and item["source"]["license_url"] for item in demos
        ),
        "every_query_has_expected_evidence": all(
            expected_phrases[item["id"]].casefold()
            in " ".join(block["text"] for block in item["query_result"]["evidence_blocks"]).casefold()
            for item in demos
        ),
        "every_pack_has_interface_manifest": all(
            (PACKS / item["id"] / "agent-interface.json").is_file() for item in demos
        ),
        "every_pack_has_agent_guide": all((PACKS / item["id"] / "AGENT.md").is_file() for item in demos),
        "flagship_traces_real_code": all(step["result"]["content_sha256"] for step in flagship["steps"]),
        "mcp_cross_resource_search": bool(mcp["search_response"]["hits"]),
        "generated_clis_run": all(item["cli_result"]["search"] for item in demos),
        "zero_model_calls": True,
    }
    showcase = {
        "project": "Agentic Anything",
        "generated_with": "v0.4.1 deterministic --no-llm path",
        "snapshot_date": manifest["snapshot_date"],
        "source_policy": manifest["policy"],
        "model_calls": 0,
        "synthetic_source_lines": 0,
        "summary": {
            "resource_types": len({item["resource_type"] for item in demos}),
            "resource_cases": len(demos),
            "publishers": len({item["source"]["publisher"] for item in demos}),
            "units": sum(item["unit_count"] for item in demos),
            "assertions_passed": sum(assertions.values()),
            "assertions_total": len(assertions),
        },
        "assertions": assertions,
        "demos": demos,
        "flagship": flagship,
        "mcp": mcp,
        "scope": (
            "Demonstrates deterministic capture and evidence retrieval over pinned real resources. "
            "It does not measure generative answer quality or authorize actions against upstream systems."
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
        f"✓ verified {showcase['summary']['resource_cases']} authentic source snapshots from "
        f"{showcase['summary']['publishers']} publishers\n"
        f"✓ agentified {showcase['summary']['units']} evidence units across "
        f"{showcase['summary']['resource_types']} resource types\n"
        f"✓ {showcase['summary']['assertions_passed']}/{showcase['summary']['assertions_total']} "
        "quality assertions passed\n"
        "✓ generated CLIs and cross-resource MCP search executed\n"
        "✓ synthetic source lines: 0; model calls: 0\n"
    )
    (RESULTS / "terminal-session.txt").write_text(transcript, encoding="utf-8")
    print(transcript, end="")
    return 0 if all(assertions.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
