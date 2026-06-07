from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b7c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("avatar_content_type", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_content_type")
    op.drop_column("users", "avatar_data")
