from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.logger import get_logger
from domain.entities.user import User
from domain.interfaces.repositories import AbstractUserRepository
from infrastructure.db.base import UserModel
from infrastructure.db.session import get_session

logger = get_logger(__name__)


def _model_to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        telegram_id=model.telegram_id,
        username=model.username,
        first_name=model.first_name,
        last_name=model.last_name,
        language_code=model.language_code,
        is_active=model.is_active,
        is_banned=model.is_banned,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _entity_to_model(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        telegram_id=entity.telegram_id,
        username=entity.username,
        first_name=entity.first_name,
        last_name=entity.last_name,
        language_code=entity.language_code,
        is_active=entity.is_active,
        is_banned=entity.is_banned,
    )


class UserRepository(AbstractUserRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        async with get_session(self._session_factory) as session:
            stmt = select(UserModel).where(UserModel.telegram_id == telegram_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _model_to_entity(model)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        async with get_session(self._session_factory) as session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _model_to_entity(model)

    async def create(self, user: User) -> User:
        async with get_session(self._session_factory) as session:
            model = _entity_to_model(user)
            session.add(model)
            await session.flush()
            await session.refresh(model)
            logger.info("user.created", telegram_id=user.telegram_id)
            return _model_to_entity(model)

    async def update(self, user: User) -> User:
        async with get_session(self._session_factory) as session:
            stmt = select(UserModel).where(UserModel.telegram_id == user.telegram_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                raise ValueError(f"User with telegram_id={user.telegram_id} not found")
            model.username = user.username
            model.first_name = user.first_name
            model.last_name = user.last_name
            model.language_code = user.language_code
            model.is_active = user.is_active
            model.is_banned = user.is_banned
            await session.flush()
            await session.refresh(model)
            return _model_to_entity(model)

    async def get_or_create(self, user: User) -> tuple[User, bool]:
        existing = await self.get_by_telegram_id(user.telegram_id)
        if existing is not None:
            return existing, False
        created = await self.create(user)
        return created, True

    async def count_active(self) -> int:
        async with get_session(self._session_factory) as session:
            stmt = select(func.count()).select_from(UserModel).where(
                UserModel.is_active.is_(True),
                UserModel.is_banned.is_(False),
            )
            result = await session.execute(stmt)
            return result.scalar_one()
