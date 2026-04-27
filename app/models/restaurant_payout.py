"""
Restaurant Payout model
Auto-created when an order is marked as DELIVERED.
Tracks platform commission (10%) and net payout to restaurant.
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Enum, ForeignKey
from app.core.database import Base
from datetime import datetime

PLATFORM_COMMISSION_RATE = 10.00  # 10% — stored in DB per record for audit trail


class RestaurantPayout(Base):
    __tablename__ = "restaurant_payouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurant_id = Column(Integer, ForeignKey("restaurant_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Amounts — all calculated at time of delivery, stored for audit
    order_amount = Column(Numeric(10, 2), nullable=False)        # subtotal (food only)
    commission_rate = Column(Numeric(5, 2), nullable=False, default=PLATFORM_COMMISSION_RATE)
    commission_amount = Column(Numeric(10, 2), nullable=False)   # order_amount × rate / 100
    payout_amount = Column(Numeric(10, 2), nullable=False)       # order_amount − commission_amount

    # Status
    status = Column(String(20), nullable=False, default="pending")  # pending / paid

    # Timestamps
    paid_at = Column(DateTime, nullable=True)
    notes = Column(String(500), nullable=True)   # payment reference or admin notes
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "restaurant_id": self.restaurant_id,
            "order_id": self.order_id,
            "order_amount": float(self.order_amount),
            "commission_rate": float(self.commission_rate),
            "commission_amount": float(self.commission_amount),
            "payout_amount": float(self.payout_amount),
            "status": self.status,
            "notes": self.notes,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
