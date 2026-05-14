"""Initial schema — Django'dan mustaqil, FastAPI o'zi yaratadi.

Barcha 19 jadval Base.metadata'dan yaratiladi. Toza Postgres'da
`alembic upgrade head` bir buyruq bilan butun schema'ni qo'yadi.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Barcha jadvallarni Base.metadata.create_all bilan yaratish.

    SQLAlchemy modellaridan to'g'ridan-to'g'ri — Django'siz.
    """
    from app.db.session import Base
    from app.models import (  # noqa: F401  — Base.metadata'ga yuklash uchun
        User, OTPCode, Species,
        Observation, ScanFeedback, TFLiteModel,
        Conversation, Message,
        Category, Product, Order, OrderItem, Review,
        Region, Crop, CropPlan,
        Ad, SavedSpecies, MapMarker,
    )
    bind = op.get_bind()
    Base.metadata.create_all(bind, checkfirst=True)


def downgrade() -> None:
    """Hamma jadvalni drop qiladi — diqqat, data yo'qoladi!"""
    from app.db.session import Base
    from app.models import (  # noqa: F401
        User, OTPCode, Species,
        Observation, ScanFeedback, TFLiteModel,
        Conversation, Message,
        Category, Product, Order, OrderItem, Review,
        Region, Crop, CropPlan,
        Ad, SavedSpecies, MapMarker,
    )
    bind = op.get_bind()
    Base.metadata.drop_all(bind, checkfirst=True)
