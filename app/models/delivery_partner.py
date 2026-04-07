"""
Delivery Partner model
Phase 1 completed: DB tables created (delivery_partners, delivery_tokens)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, TinyInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    vehicle_type = Column(String(20), nullable=False)   # bike / scooter / bicycle
    vehicle_number = Column(String(50), nullable=False)
    city = Column(String(100), nullable=False)
    status = Column(Integer, default=0, nullable=False)  # 0=pending, 1=approved, 2=rejected
    is_available = Column(Integer, default=0, nullable=False)  # online/offline
    admin_notes = Column(Text, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    tokens = relationship("DeliveryToken", back_populates="partner", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "vehicle_type": self.vehicle_type,
            "vehicle_number": self.vehicle_number,
            "city": self.city,
            "status": self.status,
            "is_available": bool(self.is_available),
            "admin_notes": self.admin_notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DeliveryToken(Base):
    __tablename__ = "delivery_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    partner_id = Column(Integer, ForeignKey("delivery_partners.id", ondelete="CASCADE"), nullable=False)
    reset_token = Column(String(4), nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    partner = relationship("DeliveryPartner", back_populates="tokens")
