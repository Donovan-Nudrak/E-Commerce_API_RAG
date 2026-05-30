"""add pgvector to products

Revision ID: add_pgvector_to_products
Revises: 656bd22f17ea
Create Date: 2026-05-29 04:34:00.000000

If you change RAG_EMBEDDING_DIM in settings, do not edit this revision.
Create a new Alembic migration instead, e.g.:
  ALTER COLUMN embedding TYPE vector(<new_dim>);
Then reindex all product embeddings.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "add_pgvector_to_products"
down_revision: Union[str, Sequence[str], None] = "656bd22f17ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "products",
        sa.Column("embedding", Vector(768), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "embedding")
    op.execute("DROP EXTENSION vector")
