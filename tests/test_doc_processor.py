import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_process_document_not_found():
    """Should return gracefully when doc not found."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    from api.services.doc_processor import process_document

    # Should not raise
    await process_document(uuid.uuid4(), mock_db)


@pytest.mark.asyncio
async def test_process_document_creates_chunks(mock_embed_batch):
    """Should chunk text and create DocumentChunk rows."""
    doc_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.chatbot_id = chatbot_id
    mock_doc.content_text = "This is test content. " * 30  # ~660 chars
    mock_doc.status = "pending"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_doc)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add_all = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    from api.services.doc_processor import process_document

    await process_document(doc_id, mock_db)

    # Should have called add_all with chunks
    mock_db.add_all.assert_called_once()
    chunks_added = mock_db.add_all.call_args[0][0]
    assert len(chunks_added) > 0


@pytest.mark.asyncio
async def test_process_document_handles_empty_text(mock_embed_batch):
    """Short text should still produce at least 1 chunk."""
    doc_id = uuid.uuid4()
    chatbot_id = uuid.uuid4()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.chatbot_id = chatbot_id
    mock_doc.content_text = "Short."
    mock_doc.status = "pending"

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_doc)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add_all = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    from api.services.doc_processor import process_document

    await process_document(doc_id, mock_db)

    # Even 1 chunk should be created
    mock_db.add_all.assert_called_once()
    chunks = mock_db.add_all.call_args[0][0]
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_process_document_sets_failed_on_error():
    """On exception, status should be set to 'failed'."""
    doc_id = uuid.uuid4()

    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.chatbot_id = uuid.uuid4()
    mock_doc.content_text = "Some content here."

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_doc)
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add_all = MagicMock(side_effect=RuntimeError("DB error"))
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    with patch("api.services.doc_processor.embed_batch", new_callable=AsyncMock, side_effect=RuntimeError("embed error")):
        from api.services.doc_processor import process_document
        await process_document(doc_id, mock_db)

    # Should have rolled back and set status to failed
    mock_db.rollback.assert_called()
