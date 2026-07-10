"""Unicode-aware lexical retrieval for heterogeneous resource packs.

The implementation is deliberately dependency-free.  It uses BM25F to keep
pack structure (title, headings, summary, body, and locator) visible to the
ranker instead of flattening every unit into one string.  Unicode word tokens
cover whitespace-delimited languages; CJK character unigrams/bigrams provide
a deterministic fallback for languages without whitespace word boundaries.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)

DEFAULT_FIELD_WEIGHTS = {
    "title": 4.0,
    "heading": 2.5,
    "summary": 1.5,
    "body": 1.0,
    "locator": 1.3,
}

DEFAULT_FIELD_B = {
    "title": 0.2,
    "heading": 0.4,
    "summary": 0.4,
    "body": 0.75,
    "locator": 0.2,
}


def _is_cjk(char: str) -> bool:
    code = ord(char)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x3040 <= code <= 0x30FF
        or 0x31F0 <= code <= 0x31FF
        or 0xAC00 <= code <= 0xD7AF
    )


def analyze(text: str, *, cjk: bool = True, cjk_unigrams: bool = False) -> list[str]:
    """Normalize text into word tokens plus optional CJK character features."""
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    tokens: list[str] = []
    for match in _WORD_RE.finditer(normalized):
        word = match.group(0)
        if any(_is_cjk(char) for char in word):
            run: list[str] = []
            for char in word:
                if _is_cjk(char):
                    run.append(char)
                else:
                    if run:
                        tokens.extend(_cjk_tokens(
                            "".join(run), cjk=cjk, cjk_unigrams=cjk_unigrams
                        ))
                        run = []
                    if char.isalnum():
                        tokens.append("w:" + char)
            if run:
                tokens.extend(_cjk_tokens(
                    "".join(run), cjk=cjk, cjk_unigrams=cjk_unigrams
                ))
        elif len(word) >= 2 or word.isdigit():
            tokens.append("w:" + word)
    return tokens


def _cjk_tokens(run: str, *, cjk: bool, cjk_unigrams: bool) -> list[str]:
    if not run:
        return []
    if not cjk:
        return ["w:" + run]
    # Unigrams make partial matching easy but create severe false positives
    # (e.g. 火星天气 matching 每三十天 through the single character 天).  Keep
    # them as an explicit ablation only; a one-character run remains usable.
    out = ["c:" + char for char in run] if cjk_unigrams or len(run) == 1 else []
    out.extend("g:" + run[i:i + 2] for i in range(len(run) - 1))
    # Exact short phrases are useful for names and error codes without making
    # the vocabulary explode on paragraphs with no spaces.
    if 1 < len(run) <= 8:
        out.append("w:" + run)
    return out


def token_weight(token: str) -> float:
    if token.startswith("c:"):
        return 0.25
    if token.startswith("g:"):
        return 0.70
    return 1.0


@dataclass(frozen=True)
class SearchDocument:
    doc_id: str
    fields: dict[str, str]


class BM25FIndex:
    """Small, deterministic BM25F index suitable for one pack or benchmark."""

    def __init__(
        self,
        documents: Iterable[SearchDocument],
        *,
        field_weights: dict[str, float] | None = None,
        field_b: dict[str, float] | None = None,
        k1: float = 1.2,
        cjk: bool = True,
        cjk_unigrams: bool = False,
    ) -> None:
        self.documents = list(documents)
        self.field_weights = field_weights or DEFAULT_FIELD_WEIGHTS
        self.field_b = field_b or DEFAULT_FIELD_B
        self.k1 = k1
        self.cjk = cjk
        self.cjk_unigrams = cjk_unigrams
        self._field_tfs: list[dict[str, Counter[str]]] = []
        self._field_lengths: list[dict[str, int]] = []
        totals: dict[str, int] = defaultdict(int)
        doc_freq: Counter[str] = Counter()
        postings: dict[str, list[int]] = defaultdict(list)

        for document_index, document in enumerate(self.documents):
            field_tfs: dict[str, Counter[str]] = {}
            field_lengths: dict[str, int] = {}
            seen: set[str] = set()
            for field in self.field_weights:
                tokens = analyze(
                    document.fields.get(field, ""), cjk=cjk, cjk_unigrams=cjk_unigrams
                )
                field_tfs[field] = Counter(tokens)
                field_lengths[field] = len(tokens)
                totals[field] += len(tokens)
                seen.update(tokens)
            self._field_tfs.append(field_tfs)
            self._field_lengths.append(field_lengths)
            doc_freq.update(seen)
            for token in seen:
                postings[token].append(document_index)

        count = max(1, len(self.documents))
        self._avg_lengths = {
            field: max(1.0, totals[field] / count) for field in self.field_weights
        }
        self._doc_freq = doc_freq
        self._postings = postings

    def search(self, query: str, *, top: int = 5) -> list[dict]:
        query_tf = Counter(analyze(
            query, cjk=self.cjk, cjk_unigrams=self.cjk_unigrams
        ))
        if not query_tf or not self.documents or top <= 0:
            return []
        count = len(self.documents)
        scores: dict[int, float] = defaultdict(float)
        matched: dict[int, list[str]] = defaultdict(list)
        # Accumulate along postings rather than scanning every candidate for
        # every query token.  This is algebraically identical and matters for
        # long passage queries such as ArguAna's.
        for token, qtf in query_tf.items():
            df = self._doc_freq.get(token, 0)
            if not df:
                continue
            idf = math.log(1.0 + (count - df + 0.5) / (df + 0.5))
            for index in self._postings[token]:
                tf_star = 0.0
                for field, weight in self.field_weights.items():
                    tf = self._field_tfs[index][field].get(token, 0)
                    if not tf:
                        continue
                    length = self._field_lengths[index][field]
                    avg_length = self._avg_lengths[field]
                    b = self.field_b.get(field, 0.75)
                    norm = (1.0 - b) + b * length / avg_length
                    tf_star += weight * tf / max(norm, 1e-9)
                if not tf_star:
                    continue
                saturation = (self.k1 + 1.0) * tf_star / (self.k1 + tf_star)
                scores[index] += idf * saturation * (1.0 + math.log(qtf)) * token_weight(token)
                matched[index].append(token)
        ranked = [
            {
                "doc_id": self.documents[index].doc_id,
                "score": round(score, 6),
                "matched_tokens": matched[index],
            }
            for index, score in scores.items()
        ]
        ranked.sort(key=lambda item: (-item["score"], item["doc_id"]))
        return ranked[:top]


def fields_from_manifest(manifest: dict) -> dict[str, str]:
    """Project a page/unit manifest into stable retrieval fields."""
    headings: list[str] = []
    body: list[str] = []
    for item in manifest.get("content", []):
        text = item.get("text", "")
        if item.get("kind") == "heading":
            headings.append(text)
        else:
            body.append(text)
    locator_parts = [
        manifest.get("url_path", ""),
        manifest.get("source_url", ""),
        manifest.get("page_type", ""),
    ]
    locator_parts.extend(link.get("text", "") for link in manifest.get("links", []))
    for form in manifest.get("forms", []):
        locator_parts.append(form.get("form_id", ""))
        locator_parts.extend(
            f"{field.get('name', '')} {field.get('label', '')}"
            for field in form.get("fields", [])
        )
    return {
        "title": manifest.get("title", ""),
        "heading": "\n".join(headings),
        "summary": manifest.get("summary", ""),
        "body": "\n".join(body),
        "locator": "\n".join(locator_parts),
    }
