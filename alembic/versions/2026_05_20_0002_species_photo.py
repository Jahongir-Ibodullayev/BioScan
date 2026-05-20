"""species_photo table — iNat enrichment uchun gallery.

Revision ID: 0002_species_photo
Revises: 0001_initial
Create Date: 2026-05-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0002_species_photo"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_species_photo",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "species_id",
            sa.BigInteger(),
            sa.ForeignKey("catalog_species.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(800), nullable=False),
        sa.Column("attribution", sa.String(300), nullable=False, server_default=""),
        sa.Column("license_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("source", sa.String(20), nullable=False, server_default="inat"),
        sa.Column("external_id", sa.String(40), nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ordering", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_species_photo_species_id", "catalog_species_photo", ["species_id"])
    op.create_index("ix_species_photo_external_id", "catalog_species_photo", ["external_id"])
    op.create_index("ix_species_photo_is_default", "catalog_species_photo", ["is_default"])
    op.create_unique_constraint(
        "uq_species_photo_species_external",
        "catalog_species_photo",
        ["species_id", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_species_photo_species_external", "catalog_species_photo", type_="unique")
    op.drop_index("ix_species_photo_is_default", table_name="catalog_species_photo")
    op.drop_index("ix_species_photo_external_id", table_name="catalog_species_photo")
    op.drop_index("ix_species_photo_species_id", table_name="catalog_species_photo")
    op.drop_table("catalog_species_photo")
