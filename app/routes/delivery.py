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
    vehicle_type: str
    vehicle_number: str
    driving_license: str = ""   # mandatory for bike/scooter
    aadhar_number: str = ""     # 12-digit Aadhar
    city: str
    area: str = ""
    upi_id: str = ""


@router.post("/apply", status_code=status.HTTP_201_CREATED)
async def apply_delivery_partner(data: DeliveryApplyRequest, db: Session = Depends(get_db)):
    """
    Submit delivery partner application.
    Status set to pending (0). Password hashed and stored.
    """
    # Validate vehicle type
    if data.vehicle_type.lower() not in VEHICLE_TYPES:
        raise HTTPException(status_code=400, detail=f"Vehicle type must be one of: {', '.join(VEHICLE_TYPES)}")

    if not data.city.strip():
        raise HTTPException(status_code=400, detail="City is required")

    if not data.area.strip():
        raise HTTPException(status_code=400, detail="Area / Locality is required")

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
        driving_license=data.driving_license.strip().upper() or None,
        aadhar_number=data.aadhar_number.strip() or None,
        city=data.city.strip(),
        area=data.area.strip() or None,
        upi_id=data.upi_id.strip() or None,
        status=0,
        is_available=0
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


# ── Phase 5: Dashboard APIs ────────────────────────────────────────────────

from fastapi import Header as FastAPIHeader

def get_delivery_partner_from_header(authorization: str, db: Session) -> DeliveryPartner:
    from app.utils.security import verify_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    payload = verify_token(authorization.split(" ")[1])
    if not payload or payload.get("type") != "delivery_partner":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    partner = db.query(DeliveryPartner).filter(
        DeliveryPartner.id == int(payload.get("sub")),
        DeliveryPartner.status == 1
    ).first()
    if not partner:
        raise HTTPException(status_code=401, detail="Access denied")
    return partner


@router.put("/toggle-availability")
def toggle_availability(authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """Toggle delivery partner online/offline status"""
    partner = get_delivery_partner_from_header(authorization, db)
    partner.is_available = 0 if partner.is_available else 1
    partner.updated_at = datetime.now()
    db.commit()
    return {"is_available": bool(partner.is_available), "message": "Online" if partner.is_available else "Offline"}


@router.get("/available-orders")
def get_available_orders(authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """
    Get orders available for pickup:
    - Status: confirmed or preparing
    - Not yet assigned to any delivery partner
    - Filtered by partner's city (and area if set)
    - Partner must have UPI ID set
    """
    from app.models.orders import Order, OrderStatus
    from app.models.restaurant_application import RestaurantApplication
    partner = get_delivery_partner_from_header(authorization, db)

    if not partner.is_available:
        return {"orders": [], "message": "Go online to see available orders"}

    # Fix 1: UPI check — block if no UPI set
    if not partner.upi_id:
        return {"orders": [], "message": "Please add your UPI ID in your profile before taking orders"}

    # Fix: Always match city + area (both mandatory — no optional condition)
    restaurant_query = db.query(RestaurantApplication.id).filter(
        RestaurantApplication.city == partner.city,
        RestaurantApplication.area == partner.area,
        RestaurantApplication.status == 1
    )
    restaurant_ids = [r[0] for r in restaurant_query.all()]

    if not restaurant_ids:
        return {"orders": [], "message": f"No restaurants found in {partner.city} - {partner.area}"}

    # Show confirmed, preparing AND ready orders — delivery partner can pick up any of these
    from app.models.orders import Order, OrderStatus
    orders = db.query(Order).filter(
        Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY]),
        Order.delivery_partner_id == None,
        Order.restaurant_id.in_(restaurant_ids)
    ).order_by(Order.created_at.asc()).all()

    return {"orders": [o.to_dict() for o in orders]}


@router.post("/accept-order/{order_id}")
async def accept_order(order_id: int, authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """
    Accept an available order.
    Assigns partner and sets status to READY (partner is heading to restaurant).
    Partner must click 'Food Picked Up' to move to OUT_FOR_DELIVERY.
    """
    from app.models.orders import Order, OrderStatus
    from app.utils.websocket_manager import manager

    partner = get_delivery_partner_from_header(authorization, db)

    if not partner.upi_id:
        raise HTTPException(status_code=400, detail="Please add your UPI ID in your profile before accepting orders")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.delivery_partner_id is not None:
        raise HTTPException(status_code=409, detail="Order already accepted by another partner")
    if order.status not in [OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY]:
        raise HTTPException(status_code=400, detail="Order is not available for pickup")

    # Assign partner — status becomes READY (partner on the way to restaurant)
    order.delivery_partner_id = partner.id
    order.status = OrderStatus.READY
    order.accepted_at = datetime.now()
    order.updated_at = datetime.now()
    db.commit()
    db.refresh(order)

    order_dict = order.to_dict()
    order_dict["delivery_partner_name"] = partner.name
    order_dict["delivery_partner_phone"] = partner.phone

    # Notify restaurant — partner is on the way to pick up
    await manager.send_restaurant_status_update(order.restaurant_id, {
        "type": "order_status_update",
        "order_id": order.id,
        "status": "ready",
        "partner_on_the_way": True,
        "order": order_dict
    })

    # Remove from available list for all other delivery partners
    await manager.broadcast_to_delivery_partners({
        "type": "order_taken",
        "order_id": order.id
    })

    return {"message": "Order accepted! Head to the restaurant.", "order": order_dict}


@router.post("/pickup-order/{order_id}")
async def pickup_order(order_id: int, authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """
    Delivery partner has physically picked up the food from the restaurant.
    Moves order READY -> OUT_FOR_DELIVERY.
    Notifies user and restaurant.
    """
    from app.models.orders import Order, OrderStatus
    from app.utils.websocket_manager import manager

    partner = get_delivery_partner_from_header(authorization, db)

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.delivery_partner_id == partner.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not assigned to you")
    if order.status != OrderStatus.READY:
        raise HTTPException(status_code=400, detail="Order is not ready for pickup or already picked up")

    order.status = OrderStatus.OUT_FOR_DELIVERY
    order.updated_at = datetime.now()
    db.commit()
    db.refresh(order)

    order_dict = order.to_dict()
    order_dict["delivery_partner_name"] = partner.name
    order_dict["delivery_partner_phone"] = partner.phone

    # Notify user — order is now on the way
    await manager.send_order_update(order_id, {
        "type": "order_status_update",
        "order_id": order_id,
        "status": "out_for_delivery",
        "order": order_dict
    })

    # Notify restaurant — food has been picked up
    await manager.send_restaurant_status_update(order.restaurant_id, {
        "type": "order_status_update",
        "order_id": order.id,
        "status": "out_for_delivery",
        "order": order_dict
    })

    return {"message": "Food picked up! Head to the customer.", "order": order_dict}


@router.put("/complete-order/{order_id}")
async def complete_order(order_id: int, authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """Mark order as delivered"""
    from app.models.orders import Order, OrderStatus
    from app.utils.websocket_manager import manager

    partner = get_delivery_partner_from_header(authorization, db)

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.delivery_partner_id == partner.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not assigned to you")
    if order.status != OrderStatus.OUT_FOR_DELIVERY:
        raise HTTPException(status_code=400, detail="Please mark food as picked up before marking as delivered")

    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now()
    order.updated_at = datetime.now()
    db.commit()
    db.refresh(order)

    # Record earnings — dedup protection, COD logic, fixed fee
    from app.models.delivery_partner import DeliveryEarning
    DELIVERY_FEE = 40.00

    existing_earning = db.query(DeliveryEarning).filter(DeliveryEarning.order_id == order.id).first()
    if not existing_earning:
        is_cod = order.payment_method and order.payment_method.lower() == 'cod'
        earning = DeliveryEarning(
            partner_id=partner.id,
            order_id=order.id,
            amount=DELIVERY_FEE,
            payment_type="cod" if is_cod else "online",
            cod_amount=float(order.total_amount) if is_cod else 0.00,
            status="pending"
        )
        db.add(earning)
        db.commit()

    # Build enriched order dict with partner info
    order_dict = order.to_dict()
    order_dict["delivery_partner_name"] = partner.name
    order_dict["delivery_partner_phone"] = partner.phone

    # Notify user via WebSocket
    await manager.send_order_update(order_id, {
        "type": "order_status_update",
        "order_id": order_id,
        "status": "delivered",
        "order": order_dict
    })

    # Notify restaurant that order was delivered (direct status update)
    await manager.send_restaurant_status_update(order.restaurant_id, {
        "type": "order_status_update",
        "order_id": order.id,
        "status": "delivered",
        "order": order_dict
    })

    return {"message": "Order marked as delivered", "order": order_dict}


@router.get("/active-order")
def get_active_order(authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """
    Get delivery partner's current active order.
    Returns READY (heading to restaurant) or OUT_FOR_DELIVERY (heading to customer).
    """
    from app.models.orders import Order, OrderStatus
    partner = get_delivery_partner_from_header(authorization, db)
    order = db.query(Order).filter(
        Order.delivery_partner_id == partner.id,
        Order.status.in_([OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY])
    ).first()
    if not order:
        return {"order": None}
    return {"order": order.to_dict()}


@router.get("/my-orders")
def get_my_orders(authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """Get delivery partner's order history"""
    from app.models.orders import Order
    partner = get_delivery_partner_from_header(authorization, db)
    orders = db.query(Order).filter(
        Order.delivery_partner_id == partner.id
    ).order_by(Order.accepted_at.desc()).limit(20).all()
    return {"orders": [o.to_dict() for o in orders]}


@router.put("/mark-cod-collected/{order_id}")
def mark_cod_collected(order_id: int, authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """Mark COD amount as collected from customer"""
    from app.models.orders import Order
    partner = get_delivery_partner_from_header(authorization, db)
    order = db.query(Order).filter(Order.id == order_id, Order.delivery_partner_id == partner.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # Fix 3: only allow for COD orders
    if not order.payment_method or order.payment_method.lower() != 'cod':
        raise HTTPException(status_code=400, detail="This is not a COD order")
    order.cod_collected = 1
    order.updated_at = datetime.now()
    db.commit()
    return {"message": "COD marked as collected"}


@router.get("/earnings")
def get_earnings(authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """Get delivery partner earnings summary"""
    from app.models.delivery_partner import DeliveryEarning
    from datetime import date
    partner = get_delivery_partner_from_header(authorization, db)

    all_earnings = db.query(DeliveryEarning).filter(DeliveryEarning.partner_id == partner.id).all()
    today = date.today()
    today_earnings = [e for e in all_earnings if e.created_at and e.created_at.date() == today]
    pending = [e for e in all_earnings if e.status == "pending"]
    cod_pending = [e for e in pending if e.payment_type == "cod"]

    return {
        "today_deliveries": len(today_earnings),
        "today_earnings": sum(float(e.amount) for e in today_earnings),
        "total_deliveries": len(all_earnings),
        "total_earnings": sum(float(e.amount) for e in all_earnings),
        "pending_payout": sum(float(e.amount) for e in pending),
        "cod_to_submit": sum(float(e.cod_amount) for e in cod_pending),
        "earnings": [e.to_dict() for e in all_earnings[-10:]]  # last 10
    }


@router.get("/profile")
def get_delivery_profile(authorization: str = FastAPIHeader(None), db: Session = Depends(get_db)):
    """Get delivery partner profile"""
    partner = get_delivery_partner_from_header(authorization, db)
    return partner.to_dict()


@router.put("/profile")
def update_delivery_profile(
    upi_id: str = None,
    city: str = None,
    area: str = None,
    phone: str = None,
    authorization: str = FastAPIHeader(None),
    db: Session = Depends(get_db)
):
    """Update delivery partner profile (UPI, city, area, phone)"""
    from app.models.orders import Order, OrderStatus
    partner = get_delivery_partner_from_header(authorization, db)

    # Block location change if partner has active delivery
    if (city is not None or area is not None):
        active = db.query(Order).filter(
            Order.delivery_partner_id == partner.id,
            Order.status == OrderStatus.OUT_FOR_DELIVERY
        ).first()
        if active:
            raise HTTPException(status_code=400, detail="Cannot change location while you have an active delivery in progress")

    if upi_id is not None:
        partner.upi_id = upi_id.strip() or None
    if city is not None:
        partner.city = city.strip()
    if area is not None:
        partner.area = area.strip() or None
    if phone is not None:
        partner.phone = phone.strip()
    partner.updated_at = datetime.now()
    db.commit()
    return {"message": "Profile updated", "partner": partner.to_dict()}
