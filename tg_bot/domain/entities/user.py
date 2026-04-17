from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    language_code: str
    is_active: bool = True
    is_banned: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.full_name

    def ban(self) -> None:
        self.is_banned = True
        self.updated_at = datetime.utcnow()

    def unban(self) -> None:
        self.is_banned = False
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()

    @classmethod
    def create(
        cls,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str],
        language_code: str = "ru",
    ) -> User:
        return cls(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
