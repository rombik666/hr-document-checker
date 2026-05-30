"""add rag source file size

Revision ID: a4c9d8e1b2f3
Revises: 9f2b7c1d4a6e
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4c9d8e1b2f3"
down_revision: Union[str, Sequence[str], None] = "9f2b7c1d4a6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rag_sources",
        sa.Column(
            "file_size_bytes",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("rag_sources", "file_size_bytes")