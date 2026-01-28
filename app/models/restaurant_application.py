from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Session
from app.core.database import Base, get_db

class RestaurantApplication(Base):
    __tablename__ = "restaurant_applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    business_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    cuisine_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    business_license = Column(String(255), nullable=False)
    food_permit = Column(String(255), nullable=False)
    status = Column(Enum('pending', 'approved', 'rejected', name='application_status'), 
                   default='pending', nullable=False, index=True)
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps (UTC)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), 
                       onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    @classmethod
    def create(cls, db: Session, business_name: str, owner_name: str, email: str, phone: str, 
               address: str, cuisine_type: str, description: str, business_license: str, 
               food_permit: str) -> 'RestaurantApplication':
        """Create a new restaurant application"""
        application = cls(
            business_name=business_name,
            owner_name=owner_name,
            email=email.lower(),
            phone=phone,
            address=address,
            cuisine_type=cuisine_type,
            description=description,
            business_license=business_license,
            food_permit=food_permit,
            status='pending'
        )
        
        db.add(application)
        db.commit()
        db.refresh(application)
        return application

    @classmethod
    def get_by_id(cls, db: Session, application_id: int) -> Optional['RestaurantApplication']:
        """Get restaurant application by ID"""
        return db.query(cls).filter(cls.id == application_id).first()

    @classmethod
    def get_by_email(cls, db: Session, email: str) -> Optional['RestaurantApplication']:
        """Get restaurant application by email (most recent)"""
        return db.query(cls).filter(cls.email == email.lower()).order_by(cls.created_at.desc()).first()

    @classmethod
    def get_all_by_status(cls, db: Session, status: str = None) -> list['RestaurantApplication']:
        """Get all restaurant applications, optionally filtered by status"""
        query = db.query(cls)
        if status:
            query = query.filter(cls.status == status)
        return query.order_by(cls.created_at.desc()).all()

    def update_status(self, db: Session, new_status: str, admin_notes: str = None, reviewed_by: int = None) -> bool:
        """Update application status"""
        self.status = new_status
        self.admin_notes = admin_notes
        self.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.reviewed_by = reviewed_by
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        db.commit()
        db.refresh(self)
        return True

    def to_dict(self) -> dict:
        """Convert application to dictionary"""
        return {
            'id': self.id,
            'business_name': self.business_name,
            'owner_name': self.owner_name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'cuisine_type': self.cuisine_type,
            'description': self.description,
            'business_license': self.business_license,
            'food_permit': self.food_permit,
            'status': self.status,
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by
        }