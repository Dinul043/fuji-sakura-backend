"""
Refresh Token model — stores hashed refresh tokens for all 4 roles.
Roles: user, restaurant, admin, delivery
DB table: refresh_tokens (already created)
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from app.core.database import Base
import hashlib
import secrets


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now())

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """SHA-256 hash — never store raw token in DB"""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @staticmethod
    def generate() -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(64)

    def is_valid(self) -> bool:
        """Check if token is not revoked and not expired"""
        return not self.revoked and datetime.now() < self.expires_at
