from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.logger import get_logger
from domain.entities.product import Product
from domain.interfaces.repositories import AbstractProductRepository
from infrastructure.db.base import ProductModel
from infrastructure.db.session import get_session

logger = get_logger(__name__)


def _model_to_entity(model: ProductModel) -> Product:
    return Product(
        id=model.id,
        title=model.title,
        price=model.price,
        url=model.url,
        source=model.source,
        image_url=model.image_url,
        rating=model.rating,
        reviews_count=model.reviews_count,
        seller=model.seller,
        available=model.available,
        scraped_at=model.scraped_at,
    )


def _entity_to_model(entity: Product) -> ProductModel:
    return ProductModel(
        title=entity.title,
        price=entity.price,
        url=entity.url,
        source=entity.source,
        image_url=entity.image_url,
        rating=entity.rating,
        reviews_count=entity.reviews_count,
        seller=entity.seller,
        available=entity.available,
    )


class ProductRepository(AbstractProductRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, product: Product) -> Product:
        async with get_session(self._session_factory) as session:
            model = _entity_to_model(product)
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return _model_to_entity(model)

    async def bulk_create(self, products: List[Product]) -> List[Product]:
        if not products:
            return []
        async with get_session(self._session_factory) as session:
            models = [_entity_to_model(p) for p in products]
            session.add_all(models)
            await session.flush()
            for model in models:
                await session.refresh(model)
            logger.info("products.bulk_created", count=len(models))
            return [_model_to_entity(m) for m in models]

    async def search(
        self,
        query: str,
        budget: Optional[float] = None,
        limit: int = 10,
    ) -> List[Product]:
        async with get_session(self._session_factory) as session:
            stmt = (
                select(ProductModel)
                .where(ProductModel.available.is_(True))
                .where(ProductModel.title.ilike(f"%{query}%"))
            )
            if budget is not None:
                stmt = stmt.where(ProductModel.price <= budget)
            stmt = stmt.order_by(ProductModel.price.asc()).limit(limit)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [_model_to_entity(m) for m in models]

    async def get_by_id(self, product_id: int) -> Optional[Product]:
        async with get_session(self._session_factory) as session:
            stmt = select(ProductModel).where(ProductModel.id == product_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _model_to_entity(model)

    async def delete_old_scrapes(self, older_than_hours: int = 24) -> int:
        threshold = datetime.utcnow() - timedelta(hours=older_than_hours)
        async with get_session(self._session_factory) as session:
            stmt = delete(ProductModel).where(ProductModel.scraped_at < threshold)
            result = await session.execute(stmt)
            count = result.rowcount
            logger.info("products.cleanup", deleted=count)
            return count
