from __future__ import annotations

import re
from collections import Counter

from app.repository import list_rag_chunks


MAX_CHUNK_CHARS = 900
MIN_TOKEN_LEN = 2


def chunk_text(content: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", content).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?。])\s+", normalized):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= MAX_CHUNK_CHARS:
            current = f"{current} {sentence}".strip()
            continue
        if current:
            chunks.append(current)
        current = sentence[:MAX_CHUNK_CHARS]
    if current:
        chunks.append(current)
    return chunks or [normalized[:MAX_CHUNK_CHARS]]


def query_rag(query: str, limit: int = 5) -> list[dict]:
    query_terms = _tokens(query)
    if not query_terms:
        return []
    query_counts = Counter(query_terms)
    matches: list[dict] = []
    for chunk in list_rag_chunks():
        content_terms = Counter(_tokens(str(chunk["content"])))
        overlap = sum(min(count, content_terms.get(term, 0)) for term, count in query_counts.items())
        if overlap <= 0:
            continue
        score = overlap / max(len(query_terms), 1)
        matches.append(
            {
                "document_id": int(chunk["document_id"]),
                "document_title": chunk["document_title"],
                "source_label": chunk.get("source_label"),
                "content": chunk["content"],
                "score": round(score, 4),
            }
        )
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:limit]


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


def _tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[\w]+", value.lower(), flags=re.UNICODE) if len(token) >= MIN_TOKEN_LEN]
