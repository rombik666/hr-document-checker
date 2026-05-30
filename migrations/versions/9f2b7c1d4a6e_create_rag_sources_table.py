"""create rag sources table

Revision ID: 9f2b7c1d4a6e
Revises: 88eb23782b4a

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f2b7c1d4a6e"
down_revision: Union[str, Sequence[str], None] = "88eb23782b4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_sources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_format", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_rag_sources_owner_user_id"),
        "rag_sources",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_sources_source_type"),
        "rag_sources",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_sources_source_format"),
        "rag_sources",
        ["source_format"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_sources_content_hash"),
        "rag_sources",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rag_sources_is_active"),
        "rag_sources",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rag_sources_is_active"), table_name="rag_sources")
    op.drop_index(op.f("ix_rag_sources_content_hash"), table_name="rag_sources")
    op.drop_index(op.f("ix_rag_sources_source_format"), table_name="rag_sources")
    op.drop_index(op.f("ix_rag_sources_source_type"), table_name="rag_sources")
    op.drop_index(op.f("ix_rag_sources_owner_user_id"), table_name="rag_sources")
    op.drop_table("rag_sources")