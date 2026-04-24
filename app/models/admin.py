from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import Session, relationship
from app.core.database import Base
from app.utils.security import verify_password, get_password_hash

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_super_admin = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps (UTC)
    created_at = Column(DateTime, default=lambda: datetime.now(), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(),
                       onupdate=lambda: datetime.now())
    last_login = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)

    # Relationship — AdminToken imported here to ensure it's registered before mapper resolves
    tokens = relationship("AdminToken", back_populates="admin", cascade="all, delete-orphan")

    @classmethod
    def create(cls, db: Session, email: str, name: str, password: str, 
               is_super_admin: bool = False, created_by: int = None) -> 'Admin':
        """Create a new admin account"""
        hashed_password = get_password_hash(password)
        
        admin = cls(
            email=email.lower().strip(),
            name=name.strip(),
            password=hashed_password,
            is_active=True,
            is_super_admin=is_super_admin,
            created_by=created_by
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin

    @classmethod
    def get_by_email(cls, db: Session, email: str) -> Optional['Admin']:
        """Get admin by email"""
        return db.query(cls).filter(
            cls.email == email.lower().strip(),
            cls.is_active == True
        ).first()

    @classmethod
    def get_by_id(cls, db: Session, admin_id: int) -> Optional['Admin']:
        """Get admin by ID"""
        return db.query(cls).filter(
            cls.id == admin_id,
            cls.is_active == True
        ).first()

    def verify_password(self, password: str) -> bool:
        """Verify admin password"""
        return verify_password(password, self.password)

    def update_last_login(self, db: Session):
        """Update last login timestamp"""
        self.last_login = datetime.now()
        db.commit()

    def deactivate(self, db: Session):
        """Deactivate admin account"""
        self.is_active = False
        self.updated_at = datetime.now()
        db.commit()

    def to_dict(self) -> dict:
        """Convert admin to dictionary (excluding password)"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_active': self.is_active,
            'is_super_admin': self.is_super_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_by': self.created_by
        }


# Import AdminToken after Admin class definition to avoid circular imports
# This ensures SQLAlchemy can resolve the "AdminToken" string in the relationship
from app.models.admin_token import AdminToken  # noqa: F401
