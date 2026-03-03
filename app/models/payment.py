"""
Payment model for managing payment transactions
Gateway-ready payment tracking system
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum
from app.core.database import Base

class PaymentMethod(PyEnum):
    ONLINE = "ONLINE"  # Razorpay handles card/upi/wallet
    COD = "COD"        # Cash on delivery

class PaymentStatus(PyEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class Payment(Base):
    __tablename__ = "payments"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign key
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Payment details
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(Float, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Transaction info (for mock and real gateway)
    transaction_reference = Column(String(255), nullable=True)  # MOCK-UUID or Razorpay payment ID
    gateway_order_id = Column(String(255), nullable=True)       # Razorpay order ID (future)
    gateway_payment_id = Column(String(255), nullable=True)     # Razorpay payment ID (future)
    gateway_signature = Column(String(255), nullable=True)      # Razorpay signature (future)
    
    # Failure tracking
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)
    payment_initiated_at = Column(DateTime, nullable=True)
    payment_completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())
    
    # Relationship
    order = relationship("Order", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, order_id={self.order_id}, status='{self.payment_status.value}', method='{self.payment_method.value}')>"

    def to_dict(self):
        """Convert payment to dictionary for API responses"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "payment_method": self.payment_method.value,
            "amount": self.amount,
            "payment_status": self.payment_status.value,
            "transaction_reference": self.transaction_reference,
            "failure_reason": self.failure_reason,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "payment_initiated_at": self.payment_initiated_at.isoformat() if self.payment_initiated_at else None,
            "payment_completed_at": self.payment_completed_at.isoformat() if self.payment_completed_at else None,
        }
