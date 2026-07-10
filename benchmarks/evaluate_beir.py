#!/usr/bin/env python3
"""Evaluate pack retrieval methods on unpacked BEIR datasets.

Expected dataset layout is the standard BEIR zip layout with corpus.jsonl,
queries.jsonl, and qrels/test.tsv.  The script has no dependencies outside the
Python standard library and this checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_anything.retrieval import BM25FIndex, SearchDocument  # noqa: E402

_LEGACY_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


def load_dataset(path: Path):
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with (path / "qrels" / "test.tsv").open(encoding="utf-8") as handle:
        header = next(handle, None)
        for line in handle:
            query_id, corpus_id, score = line.rstrip("\n").split("\t")[:3]
            if int(score) > 0:
                qrels[query_id][corpus_id] = int(score)

    queries = {}
    with (path / "queries.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if str(item["_id"]) in qrels:
                queries[str(item["_id"])] = item["text"]

    corpus = []
    with (path / "corpus.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            corpus.append({
                "id": str(item["_id"]),
                "title": item.get("title") or "",
                "text": item.get("text") or "",
            })
    return corpus, queries, dict(qrels)


class LegacyTFIndex:
    """Efficient reproduction of the v0.3 title/summary/body TF scorer."""

    def __init__(self, corpus: list[dict]) -> None:
        postings: dict[str, list[tuple[str, float]]] = defaultdict(list)
        normalizer = math.log2(3)  # one body block in this BEIR projection
        for document in corpus:
            weights: dict[str, float] = defaultdict(float)
            for token in sorted(set(_LEGACY_TOKEN_RE.findall(document["title"].lower()))):
                weights[token] += 5.0
            for token in sorted(set(_LEGACY_TOKEN_RE.findall(document["text"][:240].lower()))):
                weights[token] += 2.0
            for token in sorted(set(_LEGACY_TOKEN_RE.findall(document["text"].lower()))):
                weights[token] += 1.0
            for token, score in weights.items():
                postings[token].append((document["id"], score / normalizer))
        self.postings = postings

    def search(self, query: str, top: int) -> list[dict]:
        scores: dict[str, float] = defaultdict(float)
        for token in sorted(set(_LEGACY_TOKEN_RE.findall(query.lower()))):
            for doc_id, contribution in self.postings.get(token, ()):
                scores[doc_id] += contribution
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top]
        return [{"doc_id": doc_id, "score": score} for doc_id, score in ranked]


def make_index(method: str, corpus: list[dict]):
    if method == "legacy_tf":
        return LegacyTFIndex(corpus)
    if method == "bm25":
        documents = [
            SearchDocument(item["id"], {"body": item["title"] + "\n" + item["text"]})
            for item in corpus
        ]
        return BM25FIndex(
            documents, field_weights={"body": 1.0}, field_b={"body": 0.75}, cjk=False
        )
    if method == "bm25f_unicode":
        documents = [
            SearchDocument(item["id"], {"title": item["title"], "body": item["text"]})
            for item in corpus
        ]
        return BM25FIndex(
            documents,
            field_weights={"title": 4.0, "body": 1.0},
            field_b={"title": 0.2, "body": 0.75},
            cjk=True,
        )
    raise ValueError(method)


def query_metrics(ranked: list[str], relevant: dict[str, int]) -> dict[str, float]:
    def dcg(items: list[str], cutoff: int) -> float:
        return sum(
            (2 ** relevant.get(doc_id, 0) - 1) / math.log2(rank + 2)
            for rank, doc_id in enumerate(items[:cutoff])
        )

    ideal = sorted(relevant.values(), reverse=True)
    idcg = sum((2 ** score - 1) / math.log2(rank + 2) for rank, score in enumerate(ideal[:10]))
    ndcg10 = dcg(ranked, 10) / idcg if idcg else 0.0
    recall100 = len(set(ranked[:100]).intersection(relevant)) / max(1, len(relevant))
    reciprocal = 0.0
    for rank, doc_id in enumerate(ranked[:10], start=1):
        if doc_id in relevant:
            reciprocal = 1.0 / rank
            break
    found = 0
    precision_sum = 0.0
    for rank, doc_id in enumerate(ranked[:100], start=1):
        if doc_id in relevant:
            found += 1
            precision_sum += found / rank
    map100 = precision_sum / max(1, len(relevant))
    return {"ndcg@10": ndcg10, "recall@100": recall100, "mrr@10": reciprocal, "map@100": map100}


def summarize(per_query: dict[str, dict[str, float]]) -> dict[str, float]:
    keys = next(iter(per_query.values())).keys()
    return {key: sum(item[key] for item in per_query.values()) / len(per_query) for key in keys}


def paired_bootstrap(
    proposed: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, float]],
    *,
    samples: int = 2000,
    seed: int = 20260710,
) -> dict[str, dict[str, float]]:
    query_ids = sorted(set(proposed).intersection(baseline))
    rng = random.Random(seed)
    output = {}
    for metric in next(iter(proposed.values())):
        deltas = []
        for _ in range(samples):
            chosen = [rng.choice(query_ids) for _ in query_ids]
            deltas.append(sum(proposed[q][metric] - baseline[q][metric] for q in chosen) / len(chosen))
        deltas.sort()
        output[metric] = {
            "mean_delta": sum(proposed[q][metric] - baseline[q][metric] for q in query_ids) / len(query_ids),
            "ci95_low": deltas[int(0.025 * samples)],
            "ci95_high": deltas[min(samples - 1, int(0.975 * samples))],
        }
    return output


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return proc.stdout.strip() or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("datasets", nargs="+", type=Path)
    parser.add_argument("--methods", nargs="+", default=["legacy_tf", "bm25", "bm25f_unicode"],
                        choices=["legacy_tf", "bm25", "bm25f_unicode"])
    parser.add_argument("--top", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = {
        "experiment": "BEIR retrieval comparison",
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "top_k": args.top,
        "datasets": {},
    }
    for dataset_path in args.datasets:
        corpus, queries, qrels = load_dataset(dataset_path)
        record = {
            "counts": {"corpus": len(corpus), "queries": len(queries), "qrels": sum(map(len, qrels.values()))},
            "sha256": {
                "corpus.jsonl": file_sha256(dataset_path / "corpus.jsonl"),
                "queries.jsonl": file_sha256(dataset_path / "queries.jsonl"),
                "qrels/test.tsv": file_sha256(dataset_path / "qrels" / "test.tsv"),
            },
            "methods": {},
        }
        for method in args.methods:
            started = time.perf_counter()
            index = make_index(method, corpus)
            index_seconds = time.perf_counter() - started
            per_query = {}
            query_started = time.perf_counter()
            for query_id, query in queries.items():
                hits = index.search(query, top=args.top)
                per_query[query_id] = query_metrics(
                    [item["doc_id"] for item in hits], qrels[query_id]
                )
            query_seconds = time.perf_counter() - query_started
            record["methods"][method] = {
                "metrics": summarize(per_query),
                "index_seconds": index_seconds,
                "query_seconds": query_seconds,
                "milliseconds_per_query": 1000 * query_seconds / len(queries),
                "per_query": per_query,
            }
            print(dataset_path.name, method, record["methods"][method]["metrics"], file=sys.stderr)
        if "bm25f_unicode" in record["methods"] and "bm25" in record["methods"]:
            record["paired_bootstrap_vs_bm25"] = paired_bootstrap(
                record["methods"]["bm25f_unicode"]["per_query"],
                record["methods"]["bm25"]["per_query"],
            )
        payload["datasets"][dataset_path.name] = record

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
