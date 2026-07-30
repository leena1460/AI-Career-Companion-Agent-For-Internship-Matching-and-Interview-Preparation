"""Repository package."""

from app.database.repositories.user_detail_repository import UserDetailRepository
from app.database.repositories.user_repository import UserRepository

__all__ = ["UserDetailRepository", "UserRepository"]
