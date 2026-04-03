"""
Admin token model for password reset tokens
Follows the same pattern as user_tokens table
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class AdminToken(Base):
    __tablename__ = "admin_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False)

    # Reset token fields
    reset_token = Column(String(6), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now())

    # Relationship
    admin = relationship("Admin", back_populates="tokens")
