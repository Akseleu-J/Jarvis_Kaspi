from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Integer,
    String, Text, func, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="kaspi")
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    seller: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_products_source_scraped", "source", "scraped_at"),
        Index("ix_products_price", "price"),
    )


class LogModel(Base):
    __tablename__ = "logs_general"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    handler: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_logs_created_at", "created_at"),
    )
