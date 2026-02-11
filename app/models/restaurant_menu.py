from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Session, relationship
from app.core.database import Base

class RestaurantMenu(Base):
    __tablename__ = "restaurant_menus"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    restaurant_id = Column(Integer, ForeignKey("restaurant_applications.id"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)  # Appetizers, Main Course, Desserts, Beverages, etc.
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False, index=True)
    is_veg = Column(Boolean, default=True, nullable=False)  # Veg/Non-Veg classification
    
    # Timestamps (UTC)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), 
                       onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationship to restaurant application
    # restaurant = relationship("RestaurantApplication", back_populates="menu_items")

    @classmethod
    def create_menu_item(cls, db: Session, restaurant_id: int, item_name: str, description: str, 
                        price: float, category: str, image_url: str = None, is_veg: bool = True) -> 'RestaurantMenu':
        """Create a new menu item"""
        menu_item = cls(
            restaurant_id=restaurant_id,
            item_name=item_name.strip(),
            description=description.strip() if description else None,
            price=price,
            category=category.strip(),
            image_url=image_url.strip() if image_url else None,
            is_available=True,
            is_veg=is_veg
        )
        
        db.add(menu_item)
        db.commit()
        db.refresh(menu_item)
        return menu_item

    @classmethod
    def get_by_id(cls, db: Session, menu_id: int) -> Optional['RestaurantMenu']:
        """Get menu item by ID"""
        return db.query(cls).filter(cls.id == menu_id).first()

    @classmethod
    def get_restaurant_menu(cls, db: Session, restaurant_id: int, available_only: bool = False) -> List['RestaurantMenu']:
        """Get all menu items for a restaurant"""
        query = db.query(cls).filter(cls.restaurant_id == restaurant_id)
        
        if available_only:
            query = query.filter(cls.is_available == True)
        
        return query.order_by(cls.category, cls.item_name).all()

    @classmethod
    def get_by_category(cls, db: Session, restaurant_id: int, category: str, available_only: bool = False) -> List['RestaurantMenu']:
        """Get menu items by category for a restaurant"""
        query = db.query(cls).filter(
            cls.restaurant_id == restaurant_id,
            cls.category == category
        )
        
        if available_only:
            query = query.filter(cls.is_available == True)
        
        return query.order_by(cls.item_name).all()

    @classmethod
    def search_items(cls, db: Session, restaurant_id: int, search_term: str) -> List['RestaurantMenu']:
        """Search menu items by name or description"""
        search_pattern = f"%{search_term}%"
        return db.query(cls).filter(
            cls.restaurant_id == restaurant_id,
            (cls.item_name.ilike(search_pattern) | cls.description.ilike(search_pattern))
        ).order_by(cls.item_name).all()

    def update_item(self, db: Session, **kwargs) -> bool:
        """Update menu item"""
        allowed_fields = ['item_name', 'description', 'price', 'category', 'image_url', 'is_available', 'is_veg']
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                if field in ['item_name', 'description', 'category', 'image_url'] and value:
                    setattr(self, field, value.strip())
                else:
                    setattr(self, field, value)
        
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        db.refresh(self)
        return True

    def toggle_availability(self, db: Session) -> bool:
        """Toggle item availability"""
        self.is_available = not self.is_available
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        return self.is_available

    def delete_item(self, db: Session) -> bool:
        """Delete menu item"""
        db.delete(self)
        db.commit()
        return True

    def to_dict(self) -> dict:
        """Convert menu item to dictionary"""
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'item_name': self.item_name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image_url': self.image_url,
            'is_available': self.is_available,
            'isVeg': self.is_veg,  # Convert to camelCase for frontend
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MenuCategory:
    """Predefined menu categories"""
    APPETIZERS = "Appetizers"
    MAIN_COURSE = "Main Course"
    DESSERTS = "Desserts"
    BEVERAGES = "Beverages"
    SNACKS = "Snacks"
    SOUPS = "Soups"
    SALADS = "Salads"
    SIDES = "Sides"
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Get all available categories"""
        return [
            cls.APPETIZERS,
            cls.MAIN_COURSE,
            cls.DESSERTS,
            cls.BEVERAGES,
            cls.SNACKS,
            cls.SOUPS,
            cls.SALADS,
            cls.SIDES
        ]
    
    @classmethod
    def is_valid_category(cls, category: str) -> bool:
        """Check if category is valid"""
        return category in cls.get_all_categories()

    