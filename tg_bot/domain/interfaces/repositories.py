from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities.user import User
from domain.entities.product import Product


class AbstractUserRepository(ABC):

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_or_create(self, user: User) -> tuple[User, bool]:
        ...

    @abstractmethod
    async def count_active(self) -> int:
        ...


class AbstractProductRepository(ABC):

    @abstractmethod
    async def create(self, product: Product) -> Product:
        ...

    @abstractmethod
    async def bulk_create(self, products: List[Product]) -> List[Product]:
        ...

    @abstractmethod
    async def search(self, query: str, budget: Optional[float] = None, limit: int = 10) -> List[Product]:
        ...

    @abstractmethod
    async def get_by_id(self, product_id: int) -> Optional[Product]:
        ...

    @abstractmethod
    async def delete_old_scrapes(self, older_than_hours: int = 24) -> int:
        ...
