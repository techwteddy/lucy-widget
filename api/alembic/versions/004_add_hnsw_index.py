"""Add HNSW index on document_chunks.embedding

Revision ID: 004
Revises: 003
Create Date: 2026-03-15
"""
from alembic import op
from sqlalchemy import text

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CONCURRENTLY cannot run inside a transaction — commit first
    connection = op.get_bind()
    connection.execute(text("COMMIT"))

    op.execute(
        "CREATE INDEX CONCURRENTLY idx_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m=16, ef_construction=64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")
