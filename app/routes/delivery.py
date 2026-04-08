"""
Delivery Partner routes
✅ Phase 1: DB tables created — delivery_partners, delivery_tokens
✅ Phase 2: POST /api/delivery/apply — application form endpoint
✅ Phase 3: Admin approve/reject endpoints in admin_auth.py
🔜 Phase 4: POST /api/delivery/login
🔜 Phase 5: GET /api/delivery/available-orders, POST /api/delivery/accept-order/{id}, PUT /api/delivery/complete-order/{id}, PUT /api/delivery/toggle-availability
🔜 Phase 6: Order flow — partner accepts → out_for_delivery → delivered
🔜 Phase 7: Earnings — fixed fee per delivery
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
async def apply_delivery_partner(data: DeliveryApplyRequest, db: Session = Depends(get_db)):
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

    # Notify all connected admin dashboards via WebSocket
    try:
        from app.utils.websocket_manager import manager
        # Use restaurant_id=0 as a broadcast channel for admin notifications
        await manager.send_restaurant_notification(0, {
            "type": "new_delivery_application",
            "partner": partner.to_dict()
        })
    except Exception as e:
        print(f"⚠️ WebSocket notification failed: {e}")

    return {
        "message": "Application submitted successfully! We'll review and notify you via email.",
        "application_id": partner.id
    }


# ── Phase 4: Login ─────────────────────────────────────────────────────────

class DeliveryLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def delivery_login(data: DeliveryLoginRequest, db: Session = Depends(get_db)):
    """
    Delivery partner login.
    Only approved partners (status=1) can login.
    Returns JWT token.
    """
    from app.utils.security import verify_password, create_access_token
    from datetime import timedelta

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.email == data.email.lower().strip()
    ).first()

    if not partner or not verify_password(data.password.strip(), partner.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if partner.status == 0:
        raise HTTPException(status_code=403, detail="Your application is still under review. You'll be notified once approved.")
    if partner.status == 2:
        raise HTTPException(status_code=403, detail="Your application was not approved. Please contact support.")

    # Update last login
    partner.last_login = datetime.now()
    db.commit()

    token = create_access_token(
        data={"sub": str(partner.id), "type": "delivery_partner"},
        expires_delta=timedelta(hours=8)
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "email": partner.email,
            "phone": partner.phone,
            "vehicle_type": partner.vehicle_type,
            "city": partner.city,
            "is_available": bool(partner.is_available)
        }
    }


def get_current_delivery_partner(
    authorization: str = None,
    db: Session = None
) -> DeliveryPartner:
    """Dependency to get authenticated delivery partner from JWT"""
    from app.utils.security import verify_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("type") != "delivery_partner":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    partner_id = int(payload.get("sub"))
    partner = db.query(DeliveryPartner).filter(DeliveryPartner.id == partner_id).first()
    if not partner or partner.status != 1:
        raise HTTPException(status_code=401, detail="Access denied")
    return partner


# ── Forgot / Reset Password ────────────────────────────────────────────────

class DeliveryForgotRequest(BaseModel):
    email: str

class DeliveryResetRequest(BaseModel):
    email: str
    token: str
    new_password: str


@router.post("/forgot-password")
def delivery_forgot_password(data: DeliveryForgotRequest, db: Session = Depends(get_db)):
    """Send 4-digit reset code to delivery partner email (expires in 10 minutes)"""
    from app.models.delivery_partner import DeliveryToken
    from app.utils.otp import generate_reset_token
    from datetime import timedelta

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.email == data.email.lower().strip(),
        DeliveryPartner.status == 1  # only approved partners
    ).first()

    if not partner:
        # Check if email exists with different status
        any_partner = db.query(DeliveryPartner).filter(
            DeliveryPartner.email == data.email.lower().strip()
        ).first()
        if any_partner:
            if any_partner.status == 0:
                raise HTTPException(status_code=403, detail="Your application is still under review. Password reset is not available yet.")
            elif any_partner.status == 2:
                raise HTTPException(status_code=403, detail="Your application was not approved. Please contact support.")
        raise HTTPException(status_code=404, detail="No approved delivery partner account found with this email.")

    token = generate_reset_token()
    expires_at = datetime.now() + timedelta(minutes=10)

    existing = db.query(DeliveryToken).filter(DeliveryToken.partner_id == partner.id).first()
    if existing:
        existing.reset_token = token
        existing.reset_token_expires_at = expires_at
    else:
        db.add(DeliveryToken(partner_id=partner.id, reset_token=token, reset_token_expires_at=expires_at))
    db.commit()

    try:
        from app.utils.email import send_password_reset_email
        send_password_reset_email(to_email=partner.email, reset_token=token, user_name=partner.name)
    except Exception as e:
        print(f"⚠️ Failed to send reset email: {e}")

    print(f"🔑 Delivery reset token for {partner.email}: {token}")
    return {"message": "Reset code sent to your email."}


@router.post("/verify-reset-code")
def delivery_verify_reset_code(data: DeliveryResetRequest, db: Session = Depends(get_db)):
    """Verify reset code without changing password"""
    from app.models.delivery_partner import DeliveryToken
    from app.utils.otp import is_otp_expired

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.email == data.email.lower().strip()
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    token_record = db.query(DeliveryToken).filter(DeliveryToken.partner_id == partner.id).first()
    if not token_record or not token_record.reset_token:
        raise HTTPException(status_code=400, detail="No reset code found. Please request a new one.")
    if is_otp_expired(token_record.reset_token_expires_at):
        db.delete(token_record); db.commit()
        raise HTTPException(status_code=400, detail="Reset code expired. Please request a new one.")
    if token_record.reset_token != data.token:
        raise HTTPException(status_code=400, detail="Invalid reset code.")

    return {"message": "Reset code verified successfully"}


@router.post("/reset-password")
def delivery_reset_password(data: DeliveryResetRequest, db: Session = Depends(get_db)):
    """Reset delivery partner password"""
    from app.models.delivery_partner import DeliveryToken
    from app.utils.otp import is_otp_expired
    from app.utils.security import get_password_hash

    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.email == data.email.lower().strip()
    ).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    token_record = db.query(DeliveryToken).filter(DeliveryToken.partner_id == partner.id).first()
    if not token_record or not token_record.reset_token:
        raise HTTPException(status_code=400, detail="No reset code found. Please request a new one.")
    if is_otp_expired(token_record.reset_token_expires_at):
        db.delete(token_record); db.commit()
        raise HTTPException(status_code=400, detail="Reset code expired. Please request a new one.")
    if token_record.reset_token != data.token:
        raise HTTPException(status_code=400, detail="Invalid reset code.")
    if len(data.new_password.strip()) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    partner.password = get_password_hash(data.new_password.strip())
    partner.updated_at = datetime.now()
    db.delete(token_record)
    db.commit()

    return {"message": "Password reset successfully. You can now login."}
