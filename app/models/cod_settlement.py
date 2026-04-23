"""
COD Settlement model
Tracks when delivery partners pay back COD cash to the company via Razorpay
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum


class SettlementStatus(str, enum.Enum):
    CREATED = "created"
    PAID = "paid"
    FAILED = "failed"


class CodSettlement(Base):
    __tablename__ = "cod_settlements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    partner_id = Column(Integer, ForeignKey("delivery_partners.id", ondelete="CASCADE"), nullable=False, index=True)

    # Amount partner is paying back to company
    amount = Column(Numeric(10, 2), nullable=False)

    # Razorpay tracking
    razorpay_order_id = Column(String(100), unique=True, nullable=False)
    razorpay_payment_id = Column(String(100), unique=True, nullable=True)
    razorpay_signature = Column(String(500), nullable=True)

    # Settlement status
    status = Column(Enum(SettlementStatus, values_callable=lambda x: [e.value for e in x]), default=SettlementStatus.CREATED, nullable=False, index=True)

    # Business tracking — audit trail
    before_cod_due = Column(Numeric(10, 2), nullable=False)   # COD due before this payment
    after_cod_due = Column(Numeric(10, 2), nullable=True)     # COD due after this payment

    # Failure tracking
    failure_reason = Column(String(500), nullable=True)

    # Refund tracking
    refund_status = Column(String(20), default="none", nullable=False)  # none / initiated / completed / failed
    refund_id = Column(String(100), nullable=True)       # Razorpay refund ID
    refund_reason = Column(String(500), nullable=True)   # why refund was triggered
    refunded_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    paid_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "amount": float(self.amount),
            "razorpay_order_id": self.razorpay_order_id,
            "razorpay_payment_id": self.razorpay_payment_id,
            "status": self.status.value if self.status else "created",
            "before_cod_due": float(self.before_cod_due),
            "after_cod_due": float(self.after_cod_due) if self.after_cod_due is not None else None,
            "failure_reason": self.failure_reason,
            "refund_status": self.refund_status,
            "refund_id": self.refund_id,
            "refund_reason": self.refund_reason,
            "refunded_at": self.refunded_at.isoformat() if self.refunded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }
