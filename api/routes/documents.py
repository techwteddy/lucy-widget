import uuid
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from api.dependencies import get_db, get_admin_or_owner, get_redis
from api.models.database import AsyncSessionLocal
from api.models.knowledge_doc import KnowledgeDoc
from api.models.document_chunk import DocumentChunk
from api.schemas.chatbot import DocumentResponse
from api.services.doc_processor import process_document
from api.billing.kb_quota import check_knowledge_base_quota
from api.billing.quota import get_user_plan
from datetime import datetime, timezone

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _extract_text(content: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        return "\n\n".join(page.get_text() for page in doc)
    return content.decode("utf-8", errors="replace")


async def _process_document_background(doc_id: uuid.UUID) -> None:
    """Run document processing with its own DB session (not request-scoped)."""
    async with AsyncSessionLocal() as session:
        try:
            await process_document(doc_id, session)
        except Exception as e:
            logger.error(f"Background doc processing failed for {doc_id}: {e}", exc_info=True)
        finally:
            await session.close()


@router.post("/chatbots/{chatbot_id}/documents", response_model=DocumentResponse)
async def upload_document(
    chatbot_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    owner: str = Depends(get_admin_or_owner),
):
    # Check knowledge base quota
    plan = await get_user_plan(redis, owner) if "@" in owner else "business"
    quota = await check_knowledge_base_quota(chatbot_id, db, plan)
    if not quota.allowed:
        raise HTTPException(
            status_code=413,
            detail=f"Knowledge base limit reached ({quota.current_bytes // (1024*1024)}MB / {quota.limit_bytes // (1024*1024)}MB). Upgrade your plan.",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    filename = file.filename or ""
    if not (filename.endswith(".pdf") or filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files supported")

    text = _extract_text(content, filename)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    doc = KnowledgeDoc(
        id=uuid.uuid4(),
        chatbot_id=chatbot_id,
        filename=filename,
        content_text=text,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Process in background with its own session
    asyncio.create_task(_process_document_background(doc.id))

    return doc


@router.get("/chatbots/{chatbot_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    chatbot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_admin_or_owner),
):
    result = await db.execute(
        select(KnowledgeDoc)
        .where(KnowledgeDoc.chatbot_id == chatbot_id)
        .order_by(KnowledgeDoc.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/chatbots/{chatbot_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    chatbot_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_admin_or_owner),
):
    await db.execute(delete(DocumentChunk).where(DocumentChunk.doc_id == doc_id))
    await db.execute(
        delete(KnowledgeDoc).where(
            KnowledgeDoc.id == doc_id,
            KnowledgeDoc.chatbot_id == chatbot_id,
        )
    )
    await db.commit()
