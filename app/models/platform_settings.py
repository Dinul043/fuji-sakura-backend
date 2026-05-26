"""
Platform Settings & Tax Categories models.
Admin-controlled business parameters — no hardcoding.
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean
from sqlalchemy.orm import Session
from app.core.database import Base
from datetime import datetime
from typing import Optional


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    @classmethod
    def get(cls, db: Session, key: str, default: str = "0") -> str:
        """Get a setting value by key. Returns default if not found."""
        record = db.query(cls).filter(cls.setting_key == key).first()
        return record.setting_value if record else default

    @classmethod
    def get_float(cls, db: Session, key: str, default: float = 0.0) -> float:
        """Get a setting as float."""
        return float(cls.get(db, key, str(default)))

    @classmethod
    def get_int(cls, db: Session, key: str, default: int = 0) -> int:
        """Get a setting as int."""
        return int(float(cls.get(db, key, str(default))))

    @classmethod
    def set(cls, db: Session, key: str, value: str, admin_id: Optional[int] = None) -> 'PlatformSetting':
        """Set a setting value. Creates if not exists, updates if exists."""
        record = db.query(cls).filter(cls.setting_key == key).first()
        if record:
            record.setting_value = value
            record.updated_by = admin_id
        else:
            record = cls(setting_key=key, setting_value=value, updated_by=admin_id)
            db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def get_all(cls, db: Session) -> list:
        """Get all settings."""
        return db.query(cls).order_by(cls.setting_key).all()

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.setting_key,
            "value": self.setting_value,
            "description": self.description,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TaxCategory(Base):
    __tablename__ = "tax_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    tax_percent = Column(Numeric(5, 2), nullable=False, default=5.00)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

    @classmethod
    def get_rate(cls, db: Session, category_name: str) -> float:
        """Get tax rate for a category. Returns default 5% if not found."""
        record = db.query(cls).filter(cls.name == category_name, cls.is_active == True).first()
        return float(record.tax_percent) if record else 5.0

    @classmethod
    def get_all_active(cls, db: Session) -> list:
        """Get all active tax categories."""
        return db.query(cls).filter(cls.is_active == True).order_by(cls.name).all()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "tax_percent": float(self.tax_percent),
            "description": self.description,
            "is_active": bool(self.is_active),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
