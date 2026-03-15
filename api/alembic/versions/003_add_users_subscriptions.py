"""Add users and subscriptions tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("supabase_id", sa.String(200), unique=True, nullable=False),
        sa.Column("plan_tier", sa.String(50), default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_supabase_id", "users", ["supabase_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(200), nullable=False),
        sa.Column("stripe_customer_id", sa.String(200)),
        sa.Column("stripe_subscription_id", sa.String(200)),
        sa.Column("plan_tier", sa.String(50), default="free"),
        sa.Column("status", sa.String(50), default="active"),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_subscriptions_user_email", "subscriptions", ["user_email"])

    # Add owner_id FK column to chatbots (links to users table)
    op.add_column(
        "chatbots",
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_chatbots_owner_id", "chatbots", ["owner_id"])


def downgrade() -> None:
    op.drop_index("idx_chatbots_owner_id", table_name="chatbots")
    op.drop_column("chatbots", "owner_id")
    op.drop_table("subscriptions")
    op.drop_table("users")
