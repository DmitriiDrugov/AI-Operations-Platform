"""
Notion Ingestion Job — fetches a Notion page, chunks its content, embeds it,
and upserts into knowledge.chunks (pgvector).

Called by the worker when triggered via n8n webhook after a Notion page change.
"""
import hashlib
import time
import uuid
from dataclasses import dataclass

import asyncpg
from langchain_openai import OpenAIEmbeddings
from notion_client import AsyncClient as NotionClient

from ..core.config import get_settings
from ..core.logging import get_logger

log = get_logger(__name__)

CHUNK_TARGET_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50
MIN_CHUNK_TOKENS = 50


@dataclass
class ContentChunk:
    page_title: str
    section_heading: str | None
    content_text: str
    token_count: int
    source_id: str
    source_url: str | None


async def sync_notion_page(
    db_conn: asyncpg.Connection,
    page_id: str,
    organisation_id: str,
) -> dict:
    settings = get_settings()
    job_id = uuid.uuid4()

    await _update_job_status(db_conn, job_id, "running", organisation_id, page_id)

    try:
        notion = NotionClient(auth=settings.notion_integration_token.get_secret_value())
        page = await notion.pages.retrieve(page_id=page_id)
        blocks = await _fetch_all_blocks(notion, page_id)

        page_title = _extract_page_title(page)
        source_url = page.get("url")

        chunks = _chunk_blocks(
            blocks=blocks,
            page_title=page_title,
            source_id=page_id,
            source_url=source_url,
        )

        chunks = [c for c in chunks if c.token_count >= MIN_CHUNK_TOKENS]

        if not chunks:
            log.info("notion_ingestion.no_chunks", page_id=page_id)
            await _update_job_status(db_conn, job_id, "skipped", organisation_id, page_id, pages=1)
            return {"status": "skipped", "reason": "no_content_chunks"}

        embeddings_client = OpenAIEmbeddings(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
            openai_api_key=settings.openai_api_key.get_secret_value(),
        )

        texts = [c.content_text for c in chunks]
        vectors = await embeddings_client.aembed_documents(texts)

        upserted = 0
        for chunk, vector in zip(chunks, vectors, strict=True):
            content_hash = hashlib.sha256(chunk.content_text.encode()).hexdigest()
            vector_str = f"[{','.join(str(x) for x in vector)}]"

            result = await db_conn.execute(
                """
                INSERT INTO knowledge.chunks (
                    id, organisation_id, source_type, source_id, source_url,
                    page_title, section_heading, content_text, content_hash,
                    embedding, token_count, last_indexed_at
                ) VALUES (
                    $1, $2, 'notion_page', $3, $4,
                    $5, $6, $7, $8,
                    $9::vector, $10, NOW()
                )
                ON CONFLICT (organisation_id, source_id, content_hash) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    last_indexed_at = NOW(),
                    section_heading = EXCLUDED.section_heading,
                    page_title = EXCLUDED.page_title,
                    token_count = EXCLUDED.token_count
                """,
                uuid.uuid4(),
                organisation_id,
                chunk.source_id,
                chunk.source_url,
                chunk.page_title,
                chunk.section_heading,
                chunk.content_text,
                content_hash,
                vector_str,
                chunk.token_count,
            )
            upserted += 1

        await _update_job_status(
            db_conn, job_id, "completed", organisation_id, page_id,
            pages=1, chunks=upserted,
        )
        log.info(
            "notion_ingestion.completed",
            page_id=page_id,
            page_title=page_title,
            chunks_upserted=upserted,
        )
        return {"status": "completed", "chunks_upserted": upserted, "page_title": page_title}

    except Exception as exc:
        await _update_job_status(
            db_conn, job_id, "failed", organisation_id, page_id, error=str(exc)
        )
        log.error("notion_ingestion.failed", page_id=page_id, error=str(exc))
        raise


async def _fetch_all_blocks(notion: NotionClient, block_id: str) -> list[dict]:
    """Recursively fetch all blocks including children."""
    blocks: list[dict] = []
    cursor = None
    while True:
        kwargs = {"block_id": block_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = await notion.blocks.children.list(**kwargs)
        blocks.extend(response["results"])
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return blocks


def _extract_page_title(page: dict) -> str:
    props = page.get("properties", {})
    title_prop = props.get("title") or props.get("Name") or {}
    title_items = title_prop.get("title", [])
    return "".join(item.get("plain_text", "") for item in title_items) or "Untitled"


def _chunk_blocks(
    blocks: list[dict],
    page_title: str,
    source_id: str,
    source_url: str | None,
) -> list[ContentChunk]:
    """
    Split Notion blocks into chunks at heading boundaries.
    H2/H3 headings start a new chunk; content accumulates until the next heading
    or the target token count is exceeded.
    """
    chunks: list[ContentChunk] = []
    current_heading: str | None = None
    current_text: list[str] = []

    def flush() -> None:
        text = "\n".join(current_text).strip()
        if text:
            token_count = len(text.split())
            chunks.append(ContentChunk(
                page_title=page_title,
                section_heading=current_heading,
                content_text=text,
                token_count=token_count,
                source_id=source_id,
                source_url=source_url,
            ))

    for block in blocks:
        block_type = block.get("type", "")
        rich_text = block.get(block_type, {}).get("rich_text", [])
        plain_text = "".join(item.get("plain_text", "") for item in rich_text).strip()

        if not plain_text:
            continue

        if block_type in ("heading_2", "heading_3"):
            flush()
            current_heading = plain_text
            current_text = []
        elif block_type in ("paragraph", "bulleted_list_item", "numbered_list_item",
                             "toggle", "quote", "callout"):
            current_text.append(plain_text)
            # Split if current chunk is getting too large
            if sum(len(t.split()) for t in current_text) >= CHUNK_TARGET_TOKENS:
                flush()
                current_text = []

    flush()
    return chunks


async def _update_job_status(
    db_conn: asyncpg.Connection,
    job_id: uuid.UUID,
    status: str,
    organisation_id: str,
    source_id: str,
    pages: int = 0,
    chunks: int = 0,
    error: str | None = None,
) -> None:
    await db_conn.execute(
        """
        INSERT INTO knowledge.ingestion_jobs (
            id, organisation_id, source_type, source_id, status,
            pages_processed, chunks_upserted, error_message,
            started_at, completed_at
        ) VALUES ($1, $2, 'notion_page', $3, $4, $5, $6, $7,
            CASE WHEN $4 = 'running' THEN NOW() ELSE NULL END,
            CASE WHEN $4 IN ('completed', 'failed', 'skipped') THEN NOW() ELSE NULL END
        )
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            pages_processed = EXCLUDED.pages_processed,
            chunks_upserted = EXCLUDED.chunks_upserted,
            error_message = EXCLUDED.error_message,
            completed_at = EXCLUDED.completed_at
        """,
        job_id, organisation_id, source_id, status, pages, chunks, error,
    )
