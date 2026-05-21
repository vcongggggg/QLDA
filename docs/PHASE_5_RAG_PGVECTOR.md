# Phase 5 RAG pgvector

Phase 5 upgrades TeamsWork RAG to project-scoped retrieval with optional PostgreSQL pgvector search. Local/dev remains usable without embeddings through lexical scoring.

## Local SQLite and lexical fallback

- Set `RAG_EMBEDDING_ENABLED=false` for local/dev.
- SQLite does not require pgvector and does not need external embedding services.
- RAG still chunks documents and searches with lexical/BM25, TF-IDF, and phrase scoring.
- New RAG documents require `project_id`; backend list/query/delete filters by project access.

## PostgreSQL pgvector mode

- Use PostgreSQL with `RAG_VECTOR_BACKEND=pgvector` and `RAG_EMBEDDING_ENABLED=true`.
- Production PostgreSQL must have the pgvector extension installed before vector search can be used.
- Startup creates RAG tables and attempts `CREATE EXTENSION IF NOT EXISTS vector` only when embeddings are enabled.
- If the embedding provider fails during query, the request falls back to lexical search instead of crashing.

## Environment variables

```env
RAG_VECTOR_BACKEND=pgvector
RAG_EMBEDDING_ENABLED=false
RAG_EMBEDDING_PROVIDER=openai_compatible
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_EMBEDDING_DIM=1536
RAG_SCORE_THRESHOLD=0.45
RAG_SEARCH_LIMIT=5
RAG_STORAGE_ROOT=.data/rag_uploads
RAG_PDF_ENABLED=false
```

The OpenAI-compatible embedding provider reuses `AI_BASE_URL` and `AI_API_KEY`, calling `/embeddings`.

## Migration note

Existing unscoped RAG documents are intentionally not returned by project-scoped queries until they are migrated with a `project_id` and matching `rag_document_permissions` row.

## Limitations

- OCR is not implemented.
- PDF ingestion is optional and disabled by default.
- Embeddings are optional; lexical fallback is the supported local path.
- No Pinecone, Weaviate, FAISS, Annoy, or other vector store is used.
