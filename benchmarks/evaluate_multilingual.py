#!/usr/bin/env python3
"""Frozen heterogeneous multilingual retrieval diagnostic (E-002/E-004)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_anything.ingest import build_pack_from_source  # noqa: E402
from agentic_anything.query import PackReader, search_pack  # noqa: E402
from agentic_anything.retrieval import BM25FIndex, SearchDocument, fields_from_manifest  # noqa: E402

METHODS = ["legacy_tf", "bm25_flat_word", "bm25_flat_unicode", "bm25f_word", "bm25f_unicode"]


def build_fixture_packs(work_dir: Path) -> dict[str, PackReader]:
    fixtures = ROOT / "benchmarks" / "fixtures"
    sources = {
        "document": fixtures / "handbook_zh.md",
        "video": fixtures / "incident.srt",
        "code": fixtures / "demo_tool",
    }
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    readers = {}
    for pack_id, source in sources.items():
        target = work_dir / pack_id
        build_pack_from_source(str(source), target, site_id=pack_id)
        readers[pack_id] = PackReader(target)
    return readers


def build_indices(readers: dict[str, PackReader], method: str):
    indices = {}
    for pack_id, reader in readers.items():
        documents = []
        for unit_id in reader.page_ids():
            manifest = reader.page(unit_id)
            fields = fields_from_manifest(manifest)
            if method.startswith("bm25_flat"):
                fields = {"body": "\n".join([
                    fields["title"], fields["heading"], fields["body"], fields["locator"]
                ])}
            documents.append(SearchDocument(unit_id, fields))
        if method == "bm25_flat_word":
            indices[pack_id] = BM25FIndex(
                documents, field_weights={"body": 1.0}, field_b={"body": 0.75}, cjk=False
            )
        elif method == "bm25_flat_unicode":
            indices[pack_id] = BM25FIndex(
                documents, field_weights={"body": 1.0}, field_b={"body": 0.75}, cjk=True
            )
        elif method == "bm25f_word":
            indices[pack_id] = BM25FIndex(documents, cjk=False)
        elif method == "bm25f_unicode":
            indices[pack_id] = BM25FIndex(documents, cjk=True)
        else:
            raise ValueError(method)
    return indices


def summarize(rows: list[dict]) -> dict:
    positive = [row for row in rows if row["relevant"]]
    negative = [row for row in rows if not row["relevant"]]
    return {
        "positive_queries": len(positive),
        "negative_queries": len(negative),
        "recall@1": sum(row["reciprocal_rank"] == 1.0 for row in positive) / len(positive),
        "recall@3": sum(row["reciprocal_rank"] > 0 for row in positive) / len(positive),
        "mrr@3": sum(row["reciprocal_rank"] for row in positive) / len(positive),
        "negative_empty_accuracy": sum(not row["hits"] for row in negative) / len(negative),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=Path, default=ROOT / "benchmarks" / "multilingual_queries.json")
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    queries = json.loads(args.queries.read_text(encoding="utf-8"))
    readers = build_fixture_packs(args.work_dir)
    available = {pack: set(reader.page_ids()) for pack, reader in readers.items()}
    for query in queries:
        missing = set(query["relevant"]) - available[query["pack"]]
        if missing:
            raise ValueError(f"{query['id']} has missing gold unit ids: {sorted(missing)}")

    payload = {
        "experiment": "Frozen multilingual heterogeneous pack retrieval",
        "query_manifest": str(args.queries.resolve()),
        "packs": {pack: sorted(ids) for pack, ids in available.items()},
        "methods": {},
    }
    for method in METHODS:
        started = time.perf_counter()
        indices = None if method == "legacy_tf" else build_indices(readers, method)
        index_seconds = time.perf_counter() - started
        rows = []
        query_started = time.perf_counter()
        for query in queries:
            if method == "legacy_tf":
                raw_hits = search_pack(readers[query["pack"]], query["query"], top=3, method="legacy")
                hit_ids = [hit["page_id"] for hit in raw_hits]
            else:
                hit_ids = [
                    hit["doc_id"] for hit in indices[query["pack"]].search(query["query"], top=3)
                ]
            reciprocal_rank = 0.0
            for rank, unit_id in enumerate(hit_ids, start=1):
                if unit_id in query["relevant"]:
                    reciprocal_rank = 1.0 / rank
                    break
            rows.append({**query, "hits": hit_ids, "reciprocal_rank": reciprocal_rank})
        query_seconds = time.perf_counter() - query_started
        by_pack = {}
        for pack in sorted(readers):
            by_pack[pack] = summarize([row for row in rows if row["pack"] == pack])
        payload["methods"][method] = {
            "overall": summarize(rows),
            "by_pack": by_pack,
            "index_seconds": index_seconds,
            "query_seconds": query_seconds,
            "rows": rows,
        }
        print(method, payload["methods"][method]["overall"], file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
