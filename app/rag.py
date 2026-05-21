from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.database import database_dialect
from app.repository import list_rag_chunks, search_rag_chunks_by_embedding
from app.settings import settings


TARGET_CHUNK_CHARS = 1000
MIN_CHUNK_CHARS = 900
MAX_CHUNK_CHARS = 1100
CHUNK_OVERLAP_CHARS = 150
MIN_TOKEN_LEN = 2
EMBEDDING_VERSION = "v1"


@dataclass(frozen=True)
class TextChunk:
    content: str
    char_count: int
    token_estimate: int


@dataclass(frozen=True)
class HybridScores:
    semantic: float = 0.0
    lexical: float = 0.0
    tfidf: float = 0.0
    phrase: float = 0.0


class EmbeddingProvider(Protocol):
    provider: str
    model: str
    dim: int
    version: str

    def embed(self, text: str) -> list[float]:
        ...


class OpenAICompatibleEmbeddingProvider:
    provider = "openai_compatible"
    version = EMBEDDING_VERSION

    def __init__(self) -> None:
        self.model = settings.rag_embedding_model
        self.dim = settings.rag_embedding_dim

    def embed(self, text: str) -> list[float]:
        base_url = settings.ai_base_url.rstrip("/")
        with httpx.Client(timeout=settings.ai_task_breakdown_timeout_seconds) as client:
            response = client.post(
                f"{base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": text},
            )
            response.raise_for_status()
        embedding = response.json()["data"][0]["embedding"]
        if not isinstance(embedding, list):
            raise ValueError("embedding provider returned invalid payload")
        values = [float(value) for value in embedding]
        if len(values) != self.dim:
            raise ValueError("embedding provider returned unexpected dimension")
        return values


def chunk_text(content: str) -> list[TextChunk]:
    normalized = re.sub(r"\s+", " ", content).strip()
    if not normalized:
        return []
    chunks: list[TextChunk] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + TARGET_CHUNK_CHARS)
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + MIN_CHUNK_CHARS, min(len(normalized), start + MAX_CHUNK_CHARS))
            if boundary > start:
                end = boundary
        text = normalized[start:end].strip()
        if text:
            chunks.append(_build_chunk(text))
        if end >= len(normalized):
            break
        start = max(start + 1, end - CHUNK_OVERLAP_CHARS)
    return chunks


def get_embedding_provider() -> EmbeddingProvider | None:
    if not settings.rag_embedding_enabled:
        return None
    if settings.rag_embedding_provider != "openai_compatible":
        return None
    if not settings.ai_api_key:
        return None
    return OpenAICompatibleEmbeddingProvider()


def pgvector_enabled() -> bool:
    return (
        settings.rag_embedding_enabled
        and settings.rag_vector_backend == "pgvector"
        and database_dialect() == "postgresql"
    )


def query_rag(query: str, limit: int | None = None, current_user: dict | None = None) -> list[dict]:
    effective_limit = _effective_limit(limit)
    query_terms = _tokens(query)
    if not query_terms:
        return []

    provider = get_embedding_provider()
    query_embedding: list[float] | None = None
    semantic_rows: list[dict] = []
    semantic_enabled = False
    if provider is not None and pgvector_enabled():
        try:
            query_embedding = provider.embed(query)
            semantic_rows = search_rag_chunks_by_embedding(
                embedding=query_embedding,
                provider=provider.provider,
                model=provider.model,
                version=provider.version,
                limit=max(effective_limit * 5, 20),
                current_user=current_user,
            )
            semantic_enabled = bool(semantic_rows)
        except Exception:
            semantic_rows = []
            semantic_enabled = False

    lexical_rows = list_rag_chunks(limit=500, current_user=current_user)
    candidates = _merge_candidates(lexical_rows, semantic_rows)
    if not candidates:
        return []

    scored = _score_candidates(query, query_terms, candidates, semantic_enabled=semantic_enabled)
    threshold = max(0.0, min(float(settings.rag_score_threshold), 1.0))
    return [item for item in scored if item["score"] >= threshold][:effective_limit]


def build_rag_context(matches: list[dict]) -> tuple[str | None, list[str]]:
    if not matches:
        return None, []
    parts: list[str] = []
    sources: list[str] = []
    for item in matches:
        source = str(item.get("source_label") or item.get("document_title") or f"doc:{item['document_id']}")
        if source not in sources:
            sources.append(source)
        parts.append(f"[{source}] {item['content']}")
    return "\n".join(parts), sources


def combine_hybrid_score(scores: HybridScores, embedding_enabled: bool) -> float:
    if embedding_enabled:
        value = 0.60 * scores.semantic + 0.25 * scores.lexical + 0.10 * scores.tfidf + 0.05 * scores.phrase
    else:
        value = 0.75 * scores.lexical + 0.20 * scores.tfidf + 0.05 * scores.phrase
    return round(max(0.0, min(value, 1.0)), 4)


def _build_chunk(text: str) -> TextChunk:
    char_count = len(text)
    return TextChunk(content=text, char_count=char_count, token_estimate=max(1, math.ceil(char_count / 4)))


def _effective_limit(limit: int | None) -> int:
    configured = max(1, int(settings.rag_search_limit or 5))
    requested = configured if limit is None else int(limit)
    return max(1, min(requested, 10))


def _merge_candidates(lexical_rows: list[dict], semantic_rows: list[dict]) -> list[dict]:
    by_id: dict[int, dict] = {}
    for row in lexical_rows:
        by_id[int(row["id"])] = dict(row)
    for row in semantic_rows:
        chunk_id = int(row["id"])
        existing = by_id.get(chunk_id, {})
        merged = {**existing, **dict(row)}
        by_id[chunk_id] = merged
    return list(by_id.values())


def _score_candidates(
    query: str,
    query_terms: list[str],
    candidates: list[dict],
    *,
    semantic_enabled: bool,
) -> list[dict]:
    doc_freq = _document_frequencies(candidates)
    total_docs = max(1, len(candidates))
    avg_len = sum(len(_tokens(str(row.get("content") or ""))) for row in candidates) / total_docs
    query_counts = Counter(query_terms)
    scored: list[dict] = []
    for row in candidates:
        content = str(row.get("content") or "")
        content_terms = _tokens(content)
        if not content_terms:
            continue
        term_counts = Counter(content_terms)
        lexical = _bm25_score(query_counts, term_counts, doc_freq, total_docs, avg_len)
        tfidf = _tfidf_overlap(query_counts, term_counts, doc_freq, total_docs)
        phrase = _phrase_score(query, content)
        semantic = float(row.get("semantic_score") or 0.0)
        scores = HybridScores(semantic=semantic, lexical=lexical, tfidf=tfidf, phrase=phrase)
        combined = combine_hybrid_score(scores, embedding_enabled=semantic_enabled)
        if combined <= 0:
            continue
        scored.append(
            {
                "chunk_id": int(row["id"]),
                "chunk_index": int(row.get("chunk_index") or 0),
                "document_id": int(row["document_id"]),
                "document_title": row["document_title"],
                "project_id": int(row["project_id"]),
                "source_label": row.get("source_label"),
                "content": content,
                "score": combined,
                "source_info": {
                    "char_count": int(row.get("char_count") or len(content)),
                    "token_estimate": int(row.get("token_estimate") or max(1, math.ceil(len(content) / 4))),
                },
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def _document_frequencies(candidates: list[dict]) -> Counter:
    freq: Counter = Counter()
    for row in candidates:
        freq.update(set(_tokens(str(row.get("content") or ""))))
    return freq


def _bm25_score(
    query_counts: Counter,
    term_counts: Counter,
    doc_freq: Counter,
    total_docs: int,
    avg_len: float,
) -> float:
    if not term_counts:
        return 0.0
    k1 = 1.5
    b = 0.75
    doc_len = sum(term_counts.values())
    raw = 0.0
    max_raw = 0.0
    for term, query_count in query_counts.items():
        df = max(1, int(doc_freq.get(term, 0)))
        idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
        tf = int(term_counts.get(term, 0))
        denom = tf + k1 * (1 - b + b * doc_len / max(avg_len, 1.0))
        raw += idf * (tf * (k1 + 1) / denom if denom else 0.0)
        max_raw += idf * query_count
    if max_raw <= 0:
        return 0.0
    return max(0.0, min(raw / max_raw, 1.0))


def _tfidf_overlap(query_counts: Counter, term_counts: Counter, doc_freq: Counter, total_docs: int) -> float:
    total = 0.0
    matched = 0.0
    for term, query_count in query_counts.items():
        weight = math.log((total_docs + 1) / (int(doc_freq.get(term, 0)) + 1)) + 1
        total += weight * query_count
        if term_counts.get(term, 0):
            matched += weight * min(query_count, int(term_counts[term]))
    return matched / total if total else 0.0


def _phrase_score(query: str, content: str) -> float:
    query_normalized = " ".join(_tokens(query))
    content_normalized = " ".join(_tokens(content))
    if not query_normalized or query_normalized not in content_normalized:
        return 0.0
    return 1.0


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[\w]+", value.lower(), flags=re.UNICODE) if len(token) >= MIN_TOKEN_LEN]
