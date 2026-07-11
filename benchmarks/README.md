# Reproducible evaluations

These scripts evaluate retrieval and protocol compatibility without calling an
LLM or paid API. The compact summary below was updated on 2026-07-11; raw
per-query results, dataset hashes, logs, and timing records are retained by the
research run and are not bundled into the package.

## Heterogeneous resource-to-agent contract

`check_agentify.py` validates the full Agentic Anything main line rather than
one transport. It runs the same model-free `agentify` command on a website,
Markdown document, subtitle transcript, CSV table, code repository, real PDF,
and installed CLI help. The final registered run passes all 77 representation,
interface, offline-query, credential-absence, and generated-CLI assertions over
7/7 cases. This is a deterministic system check, not a measure of ingestion
fidelity or generative answer quality.

```bash
python benchmarks/check_agentify.py \
  --work-dir /tmp/aany-agentify \
  --pdf /path/to/a-real-paper.pdf \
  --output /tmp/aany-agentify.json
```

## BEIR retrieval

The frozen comparison uses the official BEIR test splits for ArguAna,
NFCorpus, and FiQA. `legacy_tf` reproduces v0.3 field TF scoring, `bm25` is a
flat strong lexical baseline, and `bm25f_unicode` is the proposed structured
ranker. Values are nDCG@10.

| Dataset | Queries | Legacy TF | Flat BM25 | BM25F-Unicode | Delta vs BM25 (95% paired-bootstrap CI) |
|---|---:|---:|---:|---:|---:|
| ArguAna | 1,406 | 0.2202 | 0.3348 | **0.3427** | +0.00785 [0.00472, 0.01113] |
| NFCorpus | 323 | 0.2479 | **0.3056** | 0.3034 | -0.00217 [-0.00756, 0.00289] |
| FiQA | 648 | 0.1145 | 0.2375 | 0.2375 | 0.00000 [0, 0] |

FiQA has no non-empty document titles, so the flat and fielded configurations
are algebraically identical there. The NFCorpus interval crosses zero; it is
reported as no reliable difference, not a win. ArguAna's positive interval
supports a dataset-specific benefit from preserving its available title field.

Download and unpack the official BEIR archives, then run:

```bash
python benchmarks/evaluate_beir.py \
  /path/to/arguana /path/to/nfcorpus /path/to/fiqa \
  --output /tmp/beir-results.json
```

The output stores SHA-256 dataset hashes, counts, all per-query metrics,
timings, and 2,000-sample paired-bootstrap intervals.

## Frozen multilingual diagnostic

`multilingual_queries.json` contains 10 positive and 3 negative queries over a
Chinese Markdown manual, a bilingual subtitle transcript, and a small code
repository. It is intentionally a diagnostic, not a population-level
benchmark.

| Method | Recall@1 (10 positive) | Empty result accuracy (3 negative) |
|---|---:|---:|
| Legacy TF | 0.60 | 1.00 |
| Flat BM25, word tokens | 0.60 | 1.00 |
| BM25F, CJK unigrams+bigrams | 1.00 | 0.667 |
| BM25F, CJK bigrams+short phrases (final) | **1.00** | **1.00** |

The failed unigram variant matched “火星天气温度” to “每三十天” through the
single character “天”. Removing unigrams from multi-character CJK runs fixed
that frozen negative without changing positive Recall@1.

```bash
python benchmarks/evaluate_multilingual.py \
  --work-dir /tmp/aany-packs \
  --output /tmp/aany-multilingual.json
```

## MCP and installed hosts

The protocol check covers initialization, notification semantics, ping,
tools, resources, prompts, invalid tools, stderr/stdout purity, and installed
host smoke checks. In the recorded environment, all 13 assertions passed:

- Codex CLI `0.144.0-alpha.4`: isolated MCP configuration accepted and shown as enabled;
- Claude Code `2.1.170`: isolated stdio server health check reported Connected.

The Codex result is deliberately described as configuration acceptance, not an
end-to-end model call.

```bash
python benchmarks/check_mcp.py \
  --work-dir /tmp/aany-mcp-check \
  --output /tmp/aany-mcp.json
```
