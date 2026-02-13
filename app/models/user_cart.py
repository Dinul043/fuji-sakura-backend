"""
User Cart model for storing cart items per user
Production-ready cart system with database persistence
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class UserCart(Base):
    __tablename__ = "user_cart"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurant_applications.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("restaurant_menus.id"), nullable=False)
    
    # Cart item details (cached for performance)
    item_name = Column(String(255), nullable=False)
    item_description = Column(Text, nullable=True)
    item_price = Column(Float, nullable=False)
    item_image_url = Column(String(500), nullable=True)
    item_category = Column(String(100), nullable=True)
    is_veg = Column(Boolean, default=True)
    
    # Cart specific data
    quantity = Column(Integer, nullable=False, default=1)
    
    # Restaurant details (cached for performance)
    restaurant_name = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="cart_items")
    restaurant = relationship("RestaurantApplication")
    menu_item = relationship("RestaurantMenu")
    
    def __repr__(self):
        return f"<UserCart(user_id={self.user_id}, item='{self.item_name}', qty={self.quantity})>"

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.item_price * self.quantity

    def to_dict(self):
        """Convert cart item to dictionary for API responses"""
        return {
            "id": self.menu_item_id,  # Use menu_item_id as id for frontend compatibility
            "cart_id": self.id,  # Unique cart entry ID
            "name": self.item_name,
            "description": self.item_description,
            "price": self.item_price,
            "image": self.item_image_url,
            "category": self.item_category,
            "isVeg": self.is_veg,
            "rating": 4.0,  # Default rating for now
            "quantity": self.quantity,
            "restaurantId": self.restaurant_id,
            "restaurantName": self.restaurant_name,
            "totalPrice": self.total_price
        }

        

