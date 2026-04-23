from fastapi import APIRouter, Depends, HTTPException, status

from ...core.database import get_db_session, set_session_context
from ...core.logging import get_logger
from ...models.requests import KnowledgeSearchRequest
from ...models.responses import KnowledgeSearchResponse
from ...services.rag_service import RAGService
from ..middleware.auth import RequestContext, get_request_context

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])
log = get_logger(__name__)


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> KnowledgeSearchResponse:
    """Semantic search over the organisation's knowledge base."""
    if str(request.organisation_id) != ctx.organisation_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organisation mismatch")

    try:
        async with get_db_session() as session:
            conn = await session.connection()
            raw_conn = await conn.get_raw_connection()
            await set_session_context(raw_conn, ctx.organisation_id, ctx.user_id, ctx.role, ctx.trace_id)
            service = RAGService(raw_conn)
            chunks, embed_ms, search_ms = await service.retrieve(
                query=request.query,
                organisation_id=request.organisation_id,
                source_types=request.source_types,
                top_k=request.limit,
                min_similarity=request.min_similarity,
            )
        return KnowledgeSearchResponse(
            results=chunks,
            query_embedding_latency_ms=embed_ms,
            search_latency_ms=search_ms,
        )
    except Exception as exc:
        log.error("knowledge.search.error", error=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR) from exc
