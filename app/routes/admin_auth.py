"""
Admin Authentication routes - separate from regular user auth
Uses the admins table instead of users table
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.admin import Admin
from app.utils.security import create_access_token

router = APIRouter()

class AdminLogin(BaseModel):
    email: str
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str
    admin: dict

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(login_data: AdminLogin, db: Session = Depends(get_db)):
    """Admin login - separate from regular user login"""
    try:
        # Get admin by email
        admin = Admin.get_by_email(db, login_data.email)
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not admin.verify_password(login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        admin.update_last_login(db)
        
        # Create access token (valid for 7 days — admin dashboard usage)
        access_token = create_access_token(
            data={"sub": admin.email, "admin_id": admin.id, "is_admin": True},
            expires_delta=timedelta(days=7)
        )
        
        return AdminLoginResponse(
            access_token=access_token,
            token_type="bearer",
            admin=admin.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Admin login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )

@router.get("/verify")
async def verify_admin_token(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Verify admin token and check if admin is still active in database"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        # Import JWT verification here to avoid circular imports
        from app.utils.security import verify_token
        
        # Decode and verify JWT token
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Extract admin info from token
        admin_email = payload.get("sub")
        admin_id = payload.get("admin_id")
        is_admin = payload.get("is_admin")
        
        if not admin_email or not admin_id or not is_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # CRITICAL: Check if admin still exists and is active in database
        admin = db.query(Admin).filter(
            Admin.id == admin_id,
            Admin.email == admin_email
        ).first()
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin account not found - access revoked"
            )
        
        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin account deactivated - access revoked"
            )
        
        # Return admin info for frontend
        return {
            "status": "valid", 
            "message": "Admin token verified",
            "admin": {
                "id": admin.id,
                "name": admin.name,
                "email": admin.email,
                "is_super_admin": admin.is_super_admin,
                "is_active": admin.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Admin token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )

@router.post("/logout")
async def admin_logout():
    """Admin logout"""
    return {"message": "Logged out successfully"}

class CreateAdminRequest(BaseModel):
    name: str
    email: str
    password: str

@router.post("/create-admin")
async def create_admin(
    admin_data: CreateAdminRequest, 
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Create a new admin account - ONLY accessible by SUPER ADMINS"""
    try:
        # Verify admin token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        # Import JWT verification here to avoid circular imports
        from app.utils.security import verify_token
        
        # Decode and verify JWT token
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Extract admin info from token
        admin_email = payload.get("sub")
        admin_id = payload.get("admin_id")
        is_admin = payload.get("is_admin")
        
        if not admin_email or not admin_id or not is_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Check if requesting admin exists, is active, AND is SUPER ADMIN
        requesting_admin = db.query(Admin).filter(
            Admin.id == admin_id,
            Admin.email == admin_email,
            Admin.is_active == True,
            Admin.is_super_admin == True  # ONLY SUPER ADMINS CAN CREATE ADMINS
        ).first()
        
        if not requesting_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can create new admin accounts"
            )
        
        # Validate input
        if not admin_data.name or not admin_data.email or not admin_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name, email, and password are required"
            )
        
        if len(admin_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Check if admin with this email already exists
        existing_admin = db.query(Admin).filter(Admin.email == admin_data.email.lower().strip()).first()
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An admin with this email already exists"
            )
        
        # Create new admin
        new_admin = Admin.create(
            db=db,
            email=admin_data.email,
            name=admin_data.name,
            password=admin_data.password,
            is_super_admin=False,  # New admins are not super admins by default
            created_by=requesting_admin.id
        )
        
        return {
            "message": "Admin created successfully",
            "admin": {
                "id": new_admin.id,
                "name": new_admin.name,
                "email": new_admin.email,
                "is_active": new_admin.is_active,
                "created_at": new_admin.created_at.isoformat() if new_admin.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Create admin error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin. Please try again."
        )

@router.get("/list-admins")
async def list_admins(
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """List all admins - ONLY accessible by SUPER ADMINS"""
    try:
        # Verify admin token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        # Import JWT verification here to avoid circular imports
        from app.utils.security import verify_token
        
        # Decode and verify JWT token
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Extract admin info from token
        admin_email = payload.get("sub")
        admin_id = payload.get("admin_id")
        is_admin = payload.get("is_admin")
        
        if not admin_email or not admin_id or not is_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Check if requesting admin exists, is active, AND is SUPER ADMIN
        requesting_admin = db.query(Admin).filter(
            Admin.id == admin_id,
            Admin.email == admin_email,
            Admin.is_active == True,
            Admin.is_super_admin == True  # ONLY SUPER ADMINS CAN VIEW ADMIN LIST
        ).first()
        
        if not requesting_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can view admin list"
            )
        
        # Get all admins (including inactive ones for super admin view)
        all_admins = db.query(Admin).order_by(Admin.created_at.desc()).all()
        
        admin_list = []
        for admin in all_admins:
            admin_dict = admin.to_dict()
            # Add creator name if available
            if admin.created_by:
                creator = db.query(Admin).filter(Admin.id == admin.created_by).first()
                admin_dict['created_by_name'] = creator.name if creator else 'Unknown'
            else:
                admin_dict['created_by_name'] = 'System'
            admin_list.append(admin_dict)
        
        return {
            "admins": admin_list,
            "total_count": len(admin_list),
            "active_count": len([a for a in admin_list if a['is_active']]),
            "requesting_admin": {
                "id": requesting_admin.id,
                "is_super_admin": requesting_admin.is_super_admin
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"List admins error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch admin list. Please try again."
        )

@router.put("/deactivate-admin/{admin_id}")
async def deactivate_admin(
    admin_id: int,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Deactivate an admin account - only accessible by super admins"""
    try:
        # Verify admin token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        # Import JWT verification here to avoid circular imports
        from app.utils.security import verify_token
        
        # Decode and verify JWT token
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Extract admin info from token
        admin_email = payload.get("sub")
        requesting_admin_id = payload.get("admin_id")
        is_admin = payload.get("is_admin")
        
        if not admin_email or not requesting_admin_id or not is_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Check if requesting admin exists, is active, and is super admin
        requesting_admin = db.query(Admin).filter(
            Admin.id == requesting_admin_id,
            Admin.email == admin_email,
            Admin.is_active == True,
            Admin.is_super_admin == True
        ).first()
        
        if not requesting_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can deactivate other admins"
            )
        
        # Prevent self-deactivation
        if admin_id == requesting_admin_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account"
            )
        
        # Find the admin to deactivate
        target_admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not target_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found"
            )
        
        if not target_admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin is already deactivated"
            )
        
        # Deactivate the admin
        target_admin.deactivate(db)
        
        return {
            "message": f"Admin '{target_admin.name}' has been deactivated successfully",
            "deactivated_admin": {
                "id": target_admin.id,
                "name": target_admin.name,
                "email": target_admin.email,
                "is_active": target_admin.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Deactivate admin error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate admin. Please try again."
        )

@router.put("/reactivate-admin/{admin_id}")
async def reactivate_admin(
    admin_id: int,
    authorization: str = Header(None), 
    db: Session = Depends(get_db)
):
    """Reactivate an admin account - only accessible by super admins"""
    try:
        # Verify admin token (same verification as deactivate)
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization.split(" ")[1]
        
        from app.utils.security import verify_token
        
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        admin_email = payload.get("sub")
        requesting_admin_id = payload.get("admin_id")
        is_admin = payload.get("is_admin")
        
        if not admin_email or not requesting_admin_id or not is_admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Check if requesting admin is super admin
        requesting_admin = db.query(Admin).filter(
            Admin.id == requesting_admin_id,
            Admin.email == admin_email,
            Admin.is_active == True,
            Admin.is_super_admin == True
        ).first()
        
        if not requesting_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can reactivate other admins"
            )
        
        # Find the admin to reactivate
        target_admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not target_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found"
            )
        
        if target_admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin is already active"
            )
        
        # Reactivate the admin
        target_admin.is_active = True
        target_admin.updated_at = datetime.now()
        db.commit()
        
        return {
            "message": f"Admin '{target_admin.name}' has been reactivated successfully",
            "reactivated_admin": {
                "id": target_admin.id,
                "name": target_admin.name,
                "email": target_admin.email,
                "is_active": target_admin.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Reactivate admin error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate admin. Please try again."
        )

class AdminForgotPassword(BaseModel):
    email: str

class AdminResetPassword(BaseModel):
    email: str
    token: str
    new_password: str

@router.post("/forgot-password")
async def admin_forgot_password(data: AdminForgotPassword, db: Session = Depends(get_db)):
    """Send password reset code to admin email"""
    from app.utils.otp import generate_reset_token, get_reset_token_expiry
    from app.utils.email import send_password_reset_email
    from app.models.admin_token import AdminToken

    admin = db.query(Admin).filter(Admin.email == data.email.lower().strip()).first()
    if not admin:
        raise HTTPException(status_code=404, detail="No admin account found with this email address")

    token = generate_reset_token()
    expiry = get_reset_token_expiry()

    # Upsert admin token record
    admin_token = db.query(AdminToken).filter(AdminToken.admin_id == admin.id).first()
    if admin_token:
        admin_token.reset_token = token
        admin_token.reset_token_expires_at = expiry
    else:
        admin_token = AdminToken(admin_id=admin.id, reset_token=token, reset_token_expires_at=expiry)
        db.add(admin_token)
    db.commit()

    send_password_reset_email(admin.email, token, admin.name)
    return {"message": "Reset code sent to your email"}


@router.post("/reset-password")
async def admin_reset_password(data: AdminResetPassword, db: Session = Depends(get_db)):
    """Reset admin password using the reset code"""
    from app.utils.otp import is_otp_expired
    from app.utils.security import get_password_hash
    from app.models.admin_token import AdminToken

    admin = db.query(Admin).filter(Admin.email == data.email.lower().strip()).first()
    if not admin:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    admin_token = db.query(AdminToken).filter(AdminToken.admin_id == admin.id).first()
    if not admin_token or not admin_token.reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    if admin_token.reset_token != data.token:
        raise HTTPException(status_code=400, detail="Invalid reset code")

    if is_otp_expired(admin_token.reset_token_expires_at):
        raise HTTPException(status_code=400, detail="Reset code has expired")

    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    admin.password = get_password_hash(data.new_password)
    admin.updated_at = datetime.now()
    admin_token.reset_token = None
    admin_token.reset_token_expires_at = None
    db.commit()

    return {"message": "Password reset successfully"}


# ── Delivery Partner Admin Endpoints ──────────────────────────────────────
# Phase 3 completed: Admin can list, approve, reject delivery partner applications

from app.models.delivery_partner import DeliveryPartner

def get_admin_from_token(authorization: str, db: Session) -> Admin:
    """Verify admin token and return admin object"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.split(" ")[1]
    from app.utils.security import verify_token
    payload = verify_token(token)
    if not payload or not payload.get("is_admin"):
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")
    admin = db.query(Admin).filter(Admin.id == payload.get("admin_id"), Admin.is_active == True).first()
    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found or deactivated")
    return admin


@router.get("/delivery-partners")
async def list_delivery_partners(
    status_filter: str = "all",
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """List delivery partner applications — filter by all/pending/approved/rejected"""
    get_admin_from_token(authorization, db)
    status_map = {"pending": 0, "approved": 1, "rejected": 2}
    query = db.query(DeliveryPartner)
    if status_filter in status_map:
        query = query.filter(DeliveryPartner.status == status_map[status_filter])
    partners = query.order_by(DeliveryPartner.created_at.desc()).all()
    return {"partners": [p.to_dict() for p in partners], "total": len(partners)}


class DeliveryReviewRequest(BaseModel):
    notes: str = ""


@router.put("/delivery/approve/{partner_id}")
async def approve_delivery_partner(
    partner_id: int,
    data: DeliveryReviewRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Approve a delivery partner application and send approval email"""
    admin = get_admin_from_token(authorization, db)
    partner = db.query(DeliveryPartner).filter(DeliveryPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")
    if partner.status == 1:
        raise HTTPException(status_code=400, detail="Already approved")

    partner.status = 1
    partner.admin_notes = data.notes.strip() or None
    partner.reviewed_by = admin.id
    partner.reviewed_at = datetime.now()
    partner.updated_at = datetime.now()
    db.commit()

    # Send approval email
    try:
        from app.utils.email import send_restaurant_approval_email
        send_restaurant_approval_email(
            email=partner.email,
            restaurant_name=f"Delivery Partner - {partner.name}",
            owner_name=partner.name
        )
    except Exception as e:
        print(f"⚠️ Failed to send approval email: {e}")

    return {"message": f"Delivery partner '{partner.name}' approved successfully", "partner": partner.to_dict()}


@router.put("/delivery/reject/{partner_id}")
async def reject_delivery_partner(
    partner_id: int,
    data: DeliveryReviewRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Reject a delivery partner application"""
    admin = get_admin_from_token(authorization, db)
    partner = db.query(DeliveryPartner).filter(DeliveryPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")
    if partner.status == 2:
        raise HTTPException(status_code=400, detail="Already rejected")

    partner.status = 2
    partner.admin_notes = data.notes.strip() or None
    partner.reviewed_by = admin.id
    partner.reviewed_at = datetime.now()
    partner.updated_at = datetime.now()
    db.commit()

    # Send rejection email
    try:
        from app.utils.email import send_restaurant_rejection_email
        send_restaurant_rejection_email(
            email=partner.email,
            restaurant_name=f"Delivery Partner - {partner.name}",
            owner_name=partner.name,
            rejection_reason=data.notes.strip() or "Your application did not meet our current requirements."
        )
    except Exception as e:
        print(f"⚠️ Failed to send rejection email: {e}")

    return {"message": f"Delivery partner '{partner.name}' rejected", "partner": partner.to_dict()}


# ── Admin Payout Tracking ──────────────────────────────────────────────────

@router.get("/delivery-payouts")
async def get_delivery_payouts(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get all delivery partners with earnings summary.
    Fix 3: COD tracked separately — NOT included in payout calculation.
    Fix 4: net_settlement = pending_payout - cod_to_collect (who owes whom).
    """
    get_admin_from_token(authorization, db)
    from app.models.delivery_partner import DeliveryPartner, DeliveryEarning

    partners = db.query(DeliveryPartner).filter(DeliveryPartner.status == 1).all()
    result = []
    for p in partners:
        earnings = db.query(DeliveryEarning).filter(DeliveryEarning.partner_id == p.id).all()
        pending_earnings = [e for e in earnings if e.status == "pending"]
        paid_earnings   = [e for e in earnings if e.status == "paid"]

        # ── Delivery Earnings (company → partner) ──────────────────────────
        # Pending = not yet paid by admin to partner
        pending_payout = float(sum(e.amount for e in pending_earnings))

        # ── COD (partner → company) ─────────────────────────────────────────
        # Total cash collected from customers across ALL deliveries (all time)
        all_cod_earnings = [e for e in earnings if e.payment_type == "cod"]
        cod_collected_total = float(sum(e.cod_amount for e in all_cod_earnings))

        # Total already paid back by partner via Razorpay
        from app.models.cod_settlement import CodSettlement
        paid_settlements = db.query(CodSettlement).filter(
            CodSettlement.partner_id == p.id,
            CodSettlement.status == 'paid'
        ).all()
        total_settled_by_partner = float(sum(s.amount for s in paid_settlements))

        # Still pending = total COD collected − total already settled
        # These are completely independent of delivery earnings
        cod_still_pending = max(0.0, round(cod_collected_total - total_settled_by_partner, 2))

        result.append({
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "phone": p.phone,
            "upi_id": p.upi_id,
            "city": p.city,
            "area": p.area,
            "total_deliveries": len(earnings),
            "pending_deliveries": len(pending_earnings),
            # Column 1: Delivery Earnings — company owes partner this
            "pending_payout": round(pending_payout, 2),
            # Column 2: COD Collected — total cash partner holds/held from customers
            "cod_collected_by_partner": round(cod_collected_total, 2),
            # Column 3: Platform Received — partner already paid back via Razorpay
            "total_settled_by_partner": round(total_settled_by_partner, 2),
            # Column 4: Still Pending — partner still owes company (COD − settled)
            "net_cod_to_return": cod_still_pending,
            "total_paid": float(sum(e.amount for e in paid_earnings)),
            "is_available": bool(p.is_available)
        })

    return {"partners": result, "total": len(result)}


class PayoutRequest(BaseModel):
    partner_id: Optional[int] = None
    notes: str = ""


@router.put("/delivery-payout/mark-paid/{partner_id}")
async def mark_payout_paid(
    partner_id: int,
    data: PayoutRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Mark all pending delivery earnings as paid to partner via UPI.
    HARD BLOCK: Cannot pay if partner still has unsettled COD cash.
    WebSocket: Notifies partner dashboard instantly after payment.
    """
    get_admin_from_token(authorization, db)
    from app.models.delivery_partner import DeliveryPartner, DeliveryEarning
    from app.models.cod_settlement import CodSettlement

    partner = db.query(DeliveryPartner).filter(DeliveryPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Delivery partner not found")

    if not partner.upi_id:
        raise HTTPException(status_code=400, detail="Partner has no UPI ID — cannot process payout")

    pending = db.query(DeliveryEarning).filter(
        DeliveryEarning.partner_id == partner_id,
        DeliveryEarning.status == "pending"
    ).all()

    if not pending:
        raise HTTPException(status_code=400, detail="Nothing to pay — no pending earnings for this partner")

    # HARD BLOCK — check if partner still has unsettled COD cash
    all_cod_earnings = db.query(DeliveryEarning).filter(
        DeliveryEarning.partner_id == partner_id,
        DeliveryEarning.payment_type == "cod"
    ).all()
    total_cod_collected = float(sum(e.cod_amount for e in all_cod_earnings))

    paid_settlements = db.query(CodSettlement).filter(
        CodSettlement.partner_id == partner_id,
        CodSettlement.status == 'paid'
    ).all()
    total_settled = float(sum(s.amount for s in paid_settlements))

    cod_still_pending = max(0.0, round(total_cod_collected - total_settled, 2))

    if cod_still_pending > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pay earnings — partner still has ₹{cod_still_pending:.2f} COD cash to return. Partner must settle COD first."
        )

    # Mark all pending earnings as paid
    total = sum(float(e.amount) for e in pending)
    paid_time = datetime.now()
    for e in pending:
        e.status = "paid"
        e.paid_at = paid_time
    db.commit()

    # WebSocket — notify partner dashboard instantly
    try:
        from app.utils.websocket_manager import manager
        # Broadcast to delivery partner channel (channel 0)
        await manager.broadcast_to_delivery_partners({
            "type": "payout_paid",
            "partner_id": partner_id,
            "amount_paid": round(total, 2),
            "message": f"₹{round(total, 2)} delivery earnings paid to your UPI ({partner.upi_id})"
        })
        # Also notify admin channel for real-time refresh
        await manager.send_restaurant_notification(0, {
            "type": "payout_paid",
            "partner_id": partner_id,
            "partner_name": partner.name,
            "amount_paid": round(total, 2)
        })
    except Exception as e:
        print(f"⚠️ WebSocket notification failed: {e}")

    return {
        "message": f"Marked {len(pending)} deliveries as paid for {partner.name}",
        "amount_paid": round(total, 2),
        "partner_upi": partner.upi_id,
        "paid_at": paid_time.isoformat(),
        "deliveries_count": len(pending)
    }


# ── Admin Live Order Tracking ──────────────────────────────────────────────

@router.get("/live-orders")
async def get_live_orders(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get all active orders with delivery partner info for admin tracking"""
    get_admin_from_token(authorization, db)
    from app.models.orders import Order, OrderStatus
    from app.models.delivery_partner import DeliveryPartner
    from app.models.restaurant_application import RestaurantApplication

    # Active orders — not pending, not delivered, not cancelled
    active_orders = db.query(Order).filter(
        Order.status.in_([
            OrderStatus.CONFIRMED, OrderStatus.PREPARING,
            OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY
        ])
    ).order_by(Order.created_at.desc()).all()

    result = []
    for order in active_orders:
        d = order.to_dict()
        if order.delivery_partner_id:
            partner = db.query(DeliveryPartner).filter(DeliveryPartner.id == order.delivery_partner_id).first()
            if partner:
                d["delivery_partner_name"] = partner.name
                d["delivery_partner_phone"] = partner.phone
                d["delivery_partner_upi"] = partner.upi_id
        result.append(d)

    return {"orders": result, "total": len(result)}


@router.get("/delivery-partner/{partner_id}/cod-settlements")
async def get_partner_cod_settlements(
    partner_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get COD settlement history for a specific delivery partner — admin only"""
    get_admin_from_token(authorization, db)
    from app.models.cod_settlement import CodSettlement
    from app.models.delivery_partner import DeliveryPartner
    from app.routes.delivery import calculate_cod_due

    partner = db.query(DeliveryPartner).filter(DeliveryPartner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    settlements = db.query(CodSettlement).filter(
        CodSettlement.partner_id == partner_id
    ).order_by(CodSettlement.created_at.desc()).all()

    current_cod_due = calculate_cod_due(partner_id, db)

    return {
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "email": partner.email,
            "phone": partner.phone,
            "upi_id": partner.upi_id
        },
        "current_cod_due": current_cod_due,
        "is_blocked": current_cod_due >= 1500,
        "settlements": [s.to_dict() for s in settlements],
        "total_settled": sum(float(s.amount) for s in settlements if s.status.value == "paid")
    }


class RefundSettlementRequest(BaseModel):
    reason: str = "Manual refund by admin"


@router.post("/cod-settlement/{settlement_id}/refund")
async def refund_cod_settlement(
    settlement_id: int,
    data: RefundSettlementRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Admin manually initiates a refund for a COD settlement.
    Use cases:
    - Incorrect amount was charged
    - Payment successful but backend update failed
    - Admin decides to reverse a settlement
    """
    get_admin_from_token(authorization, db)
    from app.models.cod_settlement import CodSettlement, SettlementStatus
    from app.services.razorpay_service import razorpay_service

    settlement = db.query(CodSettlement).filter(CodSettlement.id == settlement_id).first()
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")

    if settlement.status != SettlementStatus.PAID:
        raise HTTPException(status_code=400, detail="Only paid settlements can be refunded")

    if settlement.refund_status in ("initiated", "completed"):
        raise HTTPException(status_code=400, detail=f"Refund already {settlement.refund_status} for this settlement")

    if not settlement.razorpay_payment_id:
        raise HTTPException(status_code=400, detail="No Razorpay payment ID found — cannot process refund")

    # Initiate refund via Razorpay
    refund_result = razorpay_service.refund_payment(
        payment_id=settlement.razorpay_payment_id,
        amount=float(settlement.amount)
    )

    if refund_result.get("success"):
        refund_id = refund_result["refund"].get("id")
        settlement.refund_status = "initiated"
        settlement.refund_id = refund_id
        settlement.refund_reason = data.reason
        settlement.refunded_at = datetime.now()
        db.commit()
        return {
            "message": f"Refund of ₹{settlement.amount} initiated successfully",
            "refund_id": refund_id,
            "settlement_id": settlement_id,
            "amount": float(settlement.amount)
        }
    else:
        error = refund_result.get("error", "Unknown error")
        settlement.refund_status = "failed"
        settlement.refund_reason = f"Refund failed: {error}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Refund failed: {error}")


# ── Restaurant Payout Tracking ─────────────────────────────────────────────

@router.get("/restaurant-payouts")
async def get_restaurant_payouts(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get all approved restaurants with payout summary.
    Shows: total orders delivered, total owed, commission earned, pending payout.
    """
    get_admin_from_token(authorization, db)
    from app.models.restaurant_payout import RestaurantPayout
    from app.models.restaurant_application import RestaurantApplication, ApplicationStatus

    restaurants = db.query(RestaurantApplication).filter(
        RestaurantApplication.status == ApplicationStatus.APPROVED
    ).all()

    result = []
    for r in restaurants:
        payouts = db.query(RestaurantPayout).filter(
            RestaurantPayout.restaurant_id == r.id
        ).all()

        pending = [p for p in payouts if p.status == "pending"]
        paid = [p for p in payouts if p.status == "paid"]

        total_pending_payout = round(float(sum(p.payout_amount for p in pending)), 2)
        total_commission_earned = round(float(sum(p.commission_amount for p in payouts)), 2)
        total_paid_out = round(float(sum(p.payout_amount for p in paid)), 2)
        total_orders_delivered = len(payouts)

        result.append({
            "id": r.id,
            "business_name": r.business_name,
            "owner_name": r.owner_name,
            "email": r.email,
            "phone": r.phone,
            "upi_id": getattr(r, 'upi_id', None),
            "city": getattr(r, 'city', None),
            "total_orders_delivered": total_orders_delivered,
            "pending_orders": len(pending),
            "total_pending_payout": total_pending_payout,      # what we owe restaurant
            "total_commission_earned": total_commission_earned, # platform keeps this
            "total_paid_out": total_paid_out,                  # already paid to restaurant
        })

    return {"restaurants": result, "total": len(result)}


@router.get("/restaurant-payouts/{restaurant_id}")
async def get_restaurant_payout_detail(
    restaurant_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get order-wise payout breakdown for a specific restaurant.
    """
    get_admin_from_token(authorization, db)
    from app.models.restaurant_payout import RestaurantPayout
    from app.models.restaurant_application import RestaurantApplication, ApplicationStatus

    restaurant = db.query(RestaurantApplication).filter(
        RestaurantApplication.id == restaurant_id,
        RestaurantApplication.status == ApplicationStatus.APPROVED
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    payouts = db.query(RestaurantPayout).filter(
        RestaurantPayout.restaurant_id == restaurant_id
    ).order_by(RestaurantPayout.created_at.desc()).all()

    pending = [p for p in payouts if p.status == "pending"]

    return {
        "restaurant": {
            "id": restaurant.id,
            "business_name": restaurant.business_name,
            "owner_name": restaurant.owner_name,
            "email": restaurant.email,
            "phone": restaurant.phone,
        },
        "summary": {
            "total_orders": len(payouts),
            "pending_orders": len(pending),
            "total_pending_payout": round(float(sum(p.payout_amount for p in pending)), 2),
            "total_commission_earned": round(float(sum(p.commission_amount for p in payouts)), 2),
        },
        "payouts": [p.to_dict() for p in payouts]
    }


class RestaurantPayoutMarkPaidRequest(BaseModel):
    notes: str = ""


@router.put("/restaurant-payout/mark-paid/{restaurant_id}")
async def mark_restaurant_payout_paid(
    restaurant_id: int,
    data: RestaurantPayoutMarkPaidRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Mark all pending payouts for a restaurant as paid.
    Admin confirms they have transferred the amount via UPI.
    """
    get_admin_from_token(authorization, db)
    from app.models.restaurant_payout import RestaurantPayout
    from app.models.restaurant_application import RestaurantApplication

    restaurant = db.query(RestaurantApplication).filter(
        RestaurantApplication.id == restaurant_id
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    pending = db.query(RestaurantPayout).filter(
        RestaurantPayout.restaurant_id == restaurant_id,
        RestaurantPayout.status == "pending"
    ).all()

    if not pending:
        raise HTTPException(status_code=400, detail="No pending payouts for this restaurant")

    total = round(float(sum(p.payout_amount for p in pending)), 2)
    paid_time = datetime.now()
    for p in pending:
        p.status = "paid"
        p.paid_at = paid_time
        p.notes = data.notes.strip() if data.notes else None
    db.commit()

    return {
        "message": f"Marked {len(pending)} orders as paid for {restaurant.business_name}",
        "amount_paid": total,
        "orders_count": len(pending),
        "paid_at": paid_time.isoformat()
    }


@router.get("/refunds")
async def get_refunds(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get all cancelled online orders with refund status for admin"""
    get_admin_from_token(authorization, db)
    from app.models.orders import Order, OrderStatus
    from app.models.payment import Payment, PaymentStatus

    # Get all cancelled orders that were paid online
    cancelled_orders = db.query(Order).filter(
        Order.status == OrderStatus.CANCELLED,
        Order.payment_method == 'online'
    ).order_by(Order.cancelled_at.desc()).all()

    result = []
    for order in cancelled_orders:
        payment = db.query(Payment).filter(Payment.order_id == order.id).first()
        
        refund_status = "not_applicable"
        gateway_payment_id = None
        
        if payment:
            gateway_payment_id = payment.gateway_payment_id
            if payment.payment_status.value.upper() == 'REFUNDED':
                refund_status = "refunded"
            elif payment.payment_status.value.upper() == 'PAID' and payment.gateway_payment_id:
                refund_status = "processing"
            elif payment.payment_status.value.upper() == 'FAILED':
                refund_status = "failed"
        
        result.append({
            "order_id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "restaurant_name": order.restaurant_name,
            "total_amount": order.total_amount,
            "cancelled_by": order.cancelled_by or "user",
            "cancel_reason": order.cancel_reason,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else order.updated_at.isoformat() if order.updated_at else None,
            "refund_status": refund_status,
            "gateway_payment_id": gateway_payment_id
        })

    # Summary stats
    total_refunded = sum(r["total_amount"] for r in result if r["refund_status"] == "refunded")
    total_processing = sum(r["total_amount"] for r in result if r["refund_status"] == "processing")

    return {
        "refunds": result,
        "summary": {
            "total_count": len(result),
            "refunded_count": len([r for r in result if r["refund_status"] == "refunded"]),
            "processing_count": len([r for r in result if r["refund_status"] == "processing"]),
            "total_refunded_amount": round(total_refunded, 2),
            "total_processing_amount": round(total_processing, 2)
        }
    }

@router.post("/orders/{order_id}/retry-refund")
async def retry_refund(
    order_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Admin manually retries a refund for a cancelled online order
    where the automatic refund failed or was not processed.
    """
    get_admin_from_token(authorization, db)
    from app.models.orders import Order, OrderStatus
    from app.models.payment import Payment, PaymentStatus
    from app.services.razorpay_service import RazorpayService

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Order is not cancelled — refund not applicable")

    if not order.payment_method or order.payment_method.upper() != 'ONLINE':
        raise HTTPException(status_code=400, detail="This is a COD order — no refund needed")

    payment = db.query(Payment).filter(
        Payment.order_id == order.id,
        Payment.gateway_payment_id != None
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="No payment record found for this order")

    # Check if already refunded
    if str(payment.payment_status.value).upper() == 'REFUNDED':
        return {"message": "Already refunded", "status": "already_refunded"}

    # Attempt refund
    razorpay = RazorpayService()
    result = razorpay.refund_payment(
        payment_id=payment.gateway_payment_id,
        amount=order.total_amount
    )

    if result.get('success'):
        payment.payment_status = PaymentStatus.REFUNDED
        payment.failure_reason = "Order cancelled — refund initiated by admin"
        order.payment_status = PaymentStatus.REFUNDED
        db.commit()
        print(f"✅ Admin retry refund successful for order {order.order_number}: {result['refund'].get('id')}")
        return {
            "message": f"Refund of ₹{order.total_amount} initiated successfully",
            "refund_id": result['refund'].get('id'),
            "order_number": order.order_number,
            "amount": order.total_amount
        }
    else:
        error = result.get('error', 'Unknown error')
        print(f"❌ Admin retry refund failed for order {order.order_number}: {error}")
        raise HTTPException(status_code=500, detail=f"Refund failed: {error}")
