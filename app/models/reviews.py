from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from datetime import datetime

from app.database import Base


class Review(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'), nullable=False)
    comment: Mapped[str] = mapped_column(String, nullable=True)
    comment_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    grade: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped['User'] = relationship('User', back_populates='reviews')
    product: Mapped['Product'] = relationship('Product', back_populates='reviews')