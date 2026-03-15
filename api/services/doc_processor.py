import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from api.models.knowledge_doc import KnowledgeDoc
from api.models.document_chunk import DocumentChunk
from api.services.chunker import chunk_text
from api.services.embedder import embed_batch

logger = logging.getLogger(__name__)


async def process_document(doc_id: uuid.UUID, db: AsyncSession) -> None:
    """Chunk and embed a KnowledgeDoc, storing DocumentChunk rows."""
    result = await db.execute(select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id))
    doc = result.scalar_one_or_none()

    if not doc:
        logger.error(f"Doc {doc_id} not found")
        return

    try:
        await db.execute(
            update(KnowledgeDoc).where(KnowledgeDoc.id == doc_id).values(status="processing")
        )
        await db.commit()

        chunks = chunk_text(doc.content_text)
        if not chunks:
            chunks = [doc.content_text[:2000]]

        embeddings = await embed_batch(chunks)

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        chunk_objs = [
            DocumentChunk(
                id=uuid.uuid4(),
                doc_id=doc.id,
                chatbot_id=doc.chatbot_id,
                chunk_text=chunk,
                chunk_index=i,
                embedding=embedding,
                created_at=now,
            )
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        db.add_all(chunk_objs)
        await db.execute(
            update(KnowledgeDoc)
            .where(KnowledgeDoc.id == doc_id)
            .values(status="processed", chunk_count=len(chunks))
        )
        await db.commit()
        logger.info(f"Processed doc {doc_id}: {len(chunks)} chunks")

    except Exception as e:
        logger.error(f"Failed to process doc {doc_id}: {e}", exc_info=True)
        await db.rollback()
        await db.execute(
            update(KnowledgeDoc)
            .where(KnowledgeDoc.id == doc_id)
            .values(status="failed", error_message=str(e))
        )
        await db.commit()
