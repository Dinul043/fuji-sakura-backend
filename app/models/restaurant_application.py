from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, SmallInteger, Boolean, Numeric
from sqlalchemy.orm import Session
from app.core.database import Base, get_db

# Status constants for better code readability
class ApplicationStatus:
    PENDING = 0
    APPROVED = 1
    REJECTED = 2
    
    @classmethod
    def to_string(cls, status_int: int) -> str:
        """Convert integer status to string for display"""
        mapping = {
            cls.PENDING: 'pending',
            cls.APPROVED: 'approved', 
            cls.REJECTED: 'rejected'
        }
        return mapping.get(status_int, 'unknown')
    
    @classmethod
    def from_string(cls, status_str: str) -> int:
        """Convert string status to integer"""
        mapping = {
            'pending': cls.PENDING,
            'approved': cls.APPROVED,
            'rejected': cls.REJECTED
        }
        return mapping.get(status_str.lower(), cls.PENDING)

class RestaurantApplication(Base):
    __tablename__ = "restaurant_applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    business_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    cuisine_type = Column(String(100), nullable=False)
    city = Column(String(100), nullable=True)   # e.g. Chennai
    area = Column(String(100), nullable=True)   # e.g. Karapakkam, Velachery
    upi_id = Column(String(100), nullable=True)  # mandatory for receiving payouts from admin
    commission_rate = Column(Numeric(5, 2), nullable=False, default=10.00)  # platform commission %
    description = Column(Text, nullable=False)
    business_license = Column(String(255), nullable=False)
    food_permit = Column(String(255), nullable=False)
    restaurant_image = Column(String(500), nullable=True, comment='Restaurant banner/logo image URL')
    status = Column(SmallInteger, default=ApplicationStatus.PENDING, nullable=False, index=True, 
                   comment='0=pending, 1=approved, 2=rejected')
    admin_notes = Column(Text, nullable=True)
    
    # Restaurant operational status
    is_online = Column(Boolean, default=True, nullable=False)  # Restaurant accepting orders or not
    
    # Timestamps (UTC)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    reviewed_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    @classmethod
    def create(cls, db: Session, business_name: str, owner_name: str, email: str, password: str, phone: str, 
               address: str, cuisine_type: str, description: str, business_license: str, 
               food_permit: str) -> 'RestaurantApplication':
        """Create a new restaurant application"""
        application = cls(
            business_name=business_name,
            owner_name=owner_name,
            email=email.lower(),
            password=password,
            phone=phone,
            address=address,
            cuisine_type=cuisine_type,
            description=description,
            business_license=business_license,
            food_permit=food_permit,
            status=ApplicationStatus.PENDING
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
    def get_by_phone(cls, db: Session, phone: str) -> Optional['RestaurantApplication']:
        """Get restaurant application by phone number"""
        return db.query(cls).filter(cls.phone == phone).first()

    @classmethod
    def get_by_business_license(cls, db: Session, business_license: str) -> Optional['RestaurantApplication']:
        """Get restaurant application by business license number"""
        return db.query(cls).filter(cls.business_license == business_license).first()

    @classmethod
    def get_by_food_permit(cls, db: Session, food_permit: str) -> Optional['RestaurantApplication']:
        """Get restaurant application by food permit number"""
        return db.query(cls).filter(cls.food_permit == food_permit).first()

    @classmethod
    def get_all_by_status(cls, db: Session, status: str = None) -> list['RestaurantApplication']:
        """Get all restaurant applications, optionally filtered by status"""
        query = db.query(cls)
        if status:
            query = query.filter(cls.status == status)
        return query.order_by(cls.created_at.desc()).all()

    def update_status(self, db: Session, new_status: int, admin_notes: str = None, reviewed_by: int = None) -> bool:
        """Update application status"""
        self.status = new_status
        self.admin_notes = admin_notes
        self.reviewed_at = datetime.now()
        self.reviewed_by = reviewed_by
        self.updated_at = datetime.now()
        
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
            'city': self.city,
            'area': self.area,
            'upi_id': self.upi_id,
            'commission_rate': float(self.commission_rate) if self.commission_rate else 10.0,
            'description': self.description,
            'business_license': self.business_license,
            'food_permit': self.food_permit,
            'status': ApplicationStatus.to_string(self.status),  # Convert to string for API
            'status_int': self.status,  # Also provide integer value
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by
        }