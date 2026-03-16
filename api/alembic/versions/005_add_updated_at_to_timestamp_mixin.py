"""Add updated_at column to all tables using TimestampMixin

Revision ID: 005
Revises: 004
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

# Tables that use TimestampMixin
TABLES = ["chatbots", "knowledge_docs", "document_chunks", "conversations", "messages"]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("NOW()"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "updated_at")
