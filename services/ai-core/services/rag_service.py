"""
RAG Service — semantic retrieval over the knowledge chunks in pgvector.

This is a thin wrapper that:
1. Embeds the query using text-embedding-3-small
2. Runs a pgvector cosine similarity search scoped to the organisation
3. Returns ranked chunks for injection into a prompt
"""
import time
from uuid import UUID

import asyncpg
from langchain_openai import OpenAIEmbeddings

from ..core.config import get_settings
from ..core.logging import get_logger
from ..models.responses import KnowledgeChunkResult

log = get_logger(__name__)


class RAGService:
    def __init__(self, db_conn: asyncpg.Connection) -> None:
        self._conn = db_conn
        settings = get_settings()
        self._embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            openai_api_key=settings.openai_api_key.get_secret_value(),
        )
        self._top_k = settings.retrieval_top_k
        self._min_similarity = settings.retrieval_min_similarity

    async def retrieve(
        self,
        query: str,
        organisation_id: UUID,
        source_types: list[str] | None = None,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> tuple[list[KnowledgeChunkResult], int, int]:
        """
        Returns (chunks, embed_latency_ms, search_latency_ms).
        """
        k = top_k or self._top_k
        min_sim = min_similarity or self._min_similarity

        t0 = time.monotonic()
        embedding = await self._embed_query(query)
        embed_ms = int((time.monotonic() - t0) * 1000)

        t1 = time.monotonic()
        chunks = await self._vector_search(
            embedding=embedding,
            organisation_id=str(organisation_id),
            source_types=source_types,
            top_k=k,
            min_similarity=min_sim,
        )
        search_ms = int((time.monotonic() - t1) * 1000)

        log.info(
            "rag.retrieve.completed",
            query_preview=query[:100],
            organisation_id=str(organisation_id),
            chunks_returned=len(chunks),
            embed_latency_ms=embed_ms,
            search_latency_ms=search_ms,
        )

        return chunks, embed_ms, search_ms

    async def _embed_query(self, query: str) -> list[float]:
        return await self._embeddings.aembed_query(query)

    async def _vector_search(
        self,
        embedding: list[float],
        organisation_id: str,
        source_types: list[str] | None,
        top_k: int,
        min_similarity: float,
    ) -> list[KnowledgeChunkResult]:
        embedding_str = f"[{','.join(str(x) for x in embedding)}]"

        source_filter = ""
        params: list = [embedding_str, organisation_id, min_similarity, top_k]

        if source_types:
            placeholders = ", ".join(f"${i + 5}" for i in range(len(source_types)))
            source_filter = f"AND source_type IN ({placeholders})"
            params.extend(source_types)

        query = f"""
            SELECT
                id,
                page_title,
                section_heading,
                content_text,
                source_url,
                source_type,
                1 - (embedding <=> $1::vector) AS similarity_score
            FROM knowledge.chunks
            WHERE organisation_id = $2::uuid
              AND (1 - (embedding <=> $1::vector)) >= $3
              {source_filter}
            ORDER BY embedding <=> $1::vector
            LIMIT $4
        """

        rows = await self._conn.fetch(query, *params)

        return [
            KnowledgeChunkResult(
                chunk_id=row["id"],
                page_title=row["page_title"],
                section_heading=row["section_heading"],
                content_text=row["content_text"],
                source_url=row["source_url"],
                source_type=row["source_type"],
                similarity_score=float(row["similarity_score"]),
            )
            for row in rows
        ]
