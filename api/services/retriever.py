import uuid
from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession


async def similarity_search(
    query_embedding: list[float],
    chatbot_id: uuid.UUID,
    top_k: int,
    db: AsyncSession,
) -> list[tuple[Row, float]]:
    """Returns (chunk, distance) pairs ordered by cosine similarity."""
    # pgvector cosine distance: 0 = identical, 2 = opposite
    result = await db.execute(
        text(
            """
            SELECT id, doc_id, chatbot_id, chunk_text, chunk_index, created_at,
                   (embedding <=> CAST(:query_vec AS vector)) AS distance
            FROM document_chunks
            WHERE chatbot_id = :chatbot_id
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :k
            """
        ),
        {
            "query_vec": str(query_embedding),
            "chatbot_id": str(chatbot_id),
            "k": top_k,
        },
    )
    rows = result.fetchall()
    return [(row, float(row.distance)) for row in rows]
