"""
Delivery Partner model
Phase 1 completed: DB tables created (delivery_partners, delivery_tokens)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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
    driving_license = Column(String(50), nullable=True)   # mandatory for bike/scooter
    aadhar_number = Column(String(12), nullable=True)     # government ID verification
    profile_image = Column(String(500), nullable=True)    # photo for identity verification
    city = Column(String(100), nullable=False)
    area = Column(String(100), nullable=True)   # locality/area within city
    upi_id = Column(String(100), nullable=True)  # mandatory before taking orders
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
            "driving_license": self.driving_license,
            "aadhar_number": self.aadhar_number,
            "profile_image": self.profile_image,
            "city": self.city,
            "area": self.area,
            "upi_id": self.upi_id,
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


from sqlalchemy import Numeric

class DeliveryEarning(Base):
    __tablename__ = "delivery_earnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    partner_id = Column(Integer, ForeignKey("delivery_partners.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False, default=40.00)  # fixed delivery fee
    payment_type = Column(String(20), nullable=False, default="online")  # online / cod
    cod_amount = Column(Numeric(10, 2), default=0.00)  # amount collected from customer for COD
    payout_status = Column(String(20), default="pending")  # pending / paid
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "order_id": self.order_id,
            "amount": float(self.amount),
            "payment_type": self.payment_type,
            "cod_amount": float(self.cod_amount),
            "payout_status": self.payout_status,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
