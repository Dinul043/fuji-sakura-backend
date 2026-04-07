"""
Restaurant token model for password reset tokens
Same pattern as user_tokens table
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class RestaurantToken(Base):
    __tablename__ = "restaurant_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    restaurant_id = Column(Integer, ForeignKey("restaurant_applications.id", ondelete="CASCADE"), nullable=False)

    # Reset token fields
    reset_token = Column(String(4), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now())

    # Relationship
    restaurant = relationship("RestaurantApplication")
