"""
User token model for OTP and reset tokens
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class UserToken(Base):
    __tablename__ = "user_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # OTP fields
    otp = Column(String(4), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    
    # Reset token fields
    reset_token = Column(String(4), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="tokens")