"""add indexed_at to products

Revision ID: add_indexed_at_to_products
Revises: add_pgvector_to_products
Create Date: 2026-05-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_indexed_at_to_products"
down_revision: Union[str, Sequence[str], None] = "add_pgvector_to_products"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "indexed_at")
