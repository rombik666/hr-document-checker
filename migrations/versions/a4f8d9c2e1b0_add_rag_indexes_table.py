"""add rag indexes table

Revision ID: a4f8d9c2e1b0
Revises: 88eb23782b4a
Create Date: 2026-05-30 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4f8d9c2e1b0"
down_revision: Union[str, Sequence[str], None] = "88eb23782b4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "rag_indexes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="missing",
            nullable=False,
        ),
        sa.Column(
            "reindex_required",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("index_path", sa.String(length=1024), nullable=True),
        sa.Column("chunks_path", sa.String(length=1024), nullable=True),
        sa.Column("sources_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "sources_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "chunks_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "embedding_backend",
            sa.String(length=64),
            server_default="hashing",
            nullable=False,
        ),
        sa.Column(
            "embedding_model_name",
            sa.String(length=255),
            server_default="hashing",
            nullable=False,
        ),
        sa.Column(
            "embedding_dimension",
            sa.Integer(),
            server_default="384",
            nullable=False,
        ),
        sa.Column(
            "retriever_type",
            sa.String(length=64),
            server_default="faiss",
            nullable=False,
        ),
        sa.Column("index_metadata", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("last_reindexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id",
            name="uq_rag_indexes_owner_user_id",
        ),
    )

    op.create_index(
        op.f("ix_rag_indexes_owner_user_id"),
        "rag_indexes",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_indexes_status"),
        "rag_indexes",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_indexes_reindex_required"),
        "rag_indexes",
        ["reindex_required"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_indexes_sources_hash"),
        "rag_indexes",
        ["sources_hash"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(op.f("ix_rag_indexes_sources_hash"), table_name="rag_indexes")
    op.drop_index(op.f("ix_rag_indexes_reindex_required"), table_name="rag_indexes")
    op.drop_index(op.f("ix_rag_indexes_status"), table_name="rag_indexes")
    op.drop_index(op.f("ix_rag_indexes_owner_user_id"), table_name="rag_indexes")
    op.drop_table("rag_indexes")