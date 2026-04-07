"""
Delivery Partner routes
Phase 1 completed: DB tables created (delivery_partners, delivery_tokens)
Phase 2 completed: POST /api/delivery/apply — application form endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.delivery_partner import DeliveryPartner
from app.utils.security import get_password_hash

router = APIRouter()

VEHICLE_TYPES = ["bike", "scooter", "bicycle"]


class DeliveryApplyRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    vehicle_type: str   # bike / scooter / bicycle
    vehicle_number: str
    city: str


@router.post("/apply", status_code=status.HTTP_201_CREATED)
def apply_delivery_partner(data: DeliveryApplyRequest, db: Session = Depends(get_db)):
    """
    Submit delivery partner application.
    Status set to pending (0). Password hashed and stored.
    """
    # Validate vehicle type
    if data.vehicle_type.lower() not in VEHICLE_TYPES:
        raise HTTPException(status_code=400, detail=f"Vehicle type must be one of: {', '.join(VEHICLE_TYPES)}")

    # Validate password length
    if len(data.password.strip()) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Check duplicate email
    existing = db.query(DeliveryPartner).filter(
        DeliveryPartner.email == data.email.lower().strip()
    ).first()
    if existing:
        if existing.status == 0:
            raise HTTPException(status_code=409, detail="An application with this email is already pending review.")
        elif existing.status == 1:
            raise HTTPException(status_code=409, detail="This email is already registered as a delivery partner. Please login.")
        elif existing.status == 2:
            # Rejected — allow reapplication, delete old record
            db.delete(existing)
            db.commit()

    partner = DeliveryPartner(
        name=data.name.strip(),
        email=data.email.lower().strip(),
        password=get_password_hash(data.password.strip()),
        phone=data.phone.strip(),
        vehicle_type=data.vehicle_type.lower().strip(),
        vehicle_number=data.vehicle_number.strip().upper(),
        city=data.city.strip(),
        status=0,       # pending
        is_available=0  # offline by default
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)

    return {
        "message": "Application submitted successfully! We'll review and notify you via email.",
        "application_id": partner.id
    }
