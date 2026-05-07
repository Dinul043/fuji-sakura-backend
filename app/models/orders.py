"""
Orders model for managing customer orders
Production-ready order management system
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum as PyEnum
from app.core.database import Base

class OrderStatus(PyEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentStatus(PyEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class Order(Base):
    __tablename__ = "orders"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "ORD-2024-001"
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurant_applications.id"), nullable=False, index=True)
    
    # Order details
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Pricing
    subtotal = Column(Float, nullable=False)
    delivery_fee = Column(Float, nullable=False, default=0.0)
    tax_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False)
    
    # Delivery information
    delivery_address = Column(Text, nullable=False)
    delivery_phone = Column(String(20), nullable=False)
    
    # Customer information (cached)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    
    # Restaurant information (cached)
    restaurant_name = Column(String(255), nullable=False)
    
    # Timing
    estimated_delivery_time = Column(Integer, nullable=True)  # Minutes
    
    # Payment information
    payment_method = Column(String(50), nullable=True)  # "card", "cash", "upi", etc.
    payment_reference = Column(String(255), nullable=True)
    
    # Special instructions
    special_instructions = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())
    confirmed_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)  # when delivery partner accepted

    # Delivery partner assignment
    delivery_partner_id = Column(Integer, nullable=True)
    cod_collected = Column(Integer, default=0, nullable=True)  # 1 = COD collected by partner

    # Cancellation tracking
    cancelled_by = Column(String(20), nullable=True)   # 'user' or 'restaurant'
    cancel_reason = Column(String(255), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    restaurant = relationship("RestaurantApplication")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', status='{self.status}')>"

    def to_dict(self):
        """Convert order to dictionary for API responses"""
        # Resolve delivery partner name/phone if assigned
        partner_name = None
        partner_phone = None
        if self.delivery_partner_id:
            try:
                from app.models.delivery_partner import DeliveryPartner
                from app.core.database import SessionLocal
                db = SessionLocal()
                partner = db.query(DeliveryPartner).filter(
                    DeliveryPartner.id == self.delivery_partner_id
                ).first()
                if partner:
                    partner_name = partner.name
                    partner_phone = partner.phone
                db.close()
            except Exception:
                pass

        return {
            "id": self.id,
            "order_number": self.order_number,
            "status": self.status.value.lower(),
            "payment_status": self.payment_status.value.lower(),
            "subtotal": self.subtotal,
            "delivery_fee": self.delivery_fee,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "delivery_address": self.delivery_address,
            "delivery_phone": self.delivery_phone,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "restaurant_name": self.restaurant_name,
            "restaurant_id": self.restaurant_id,
            "estimated_delivery_time": self.estimated_delivery_time,
            "payment_method": self.payment_method,
            "special_instructions": self.special_instructions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "delivery_partner_id": self.delivery_partner_id,
            "delivery_partner_name": partner_name,
            "delivery_partner_phone": partner_phone,
            "cod_collected": bool(self.cod_collected),
            "cancelled_by": self.cancelled_by,
            "cancel_reason": self.cancel_reason,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "items": [item.to_dict() for item in self.order_items] if self.order_items else []
        }

class OrderItem(Base):
    __tablename__ = "order_items"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign keys
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("restaurant_menus.id"), nullable=False)
    
    # Item details (cached at time of order)
    item_name = Column(String(255), nullable=False)
    item_description = Column(Text, nullable=True)
    item_price = Column(Float, nullable=False)  # Price at time of order
    item_image_url = Column(String(500), nullable=True)
    item_category = Column(String(100), nullable=True)
    is_veg = Column(Boolean, default=True)
    
    # Order specific data
    quantity = Column(Integer, nullable=False, default=1)
    special_instructions = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now())
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    menu_item = relationship("RestaurantMenu")
    
    def __repr__(self):
        return f"<OrderItem(order_id={self.order_id}, item='{self.item_name}', qty={self.quantity})>"

    @property
    def total_price(self):
        """Calculate total price for this order item"""
        return self.item_price * self.quantity

    def to_dict(self):
        """Convert order item to dictionary for API responses"""
        return {
            "id": self.id,
            "menu_item_id": self.menu_item_id,
            "name": self.item_name,
            "description": self.item_description,
            "price": self.item_price,
            "image": self.item_image_url,
            "category": self.item_category,
            "isVeg": self.is_veg,
            "quantity": self.quantity,
            "total_price": self.total_price,
            "special_instructions": self.special_instructions
        }