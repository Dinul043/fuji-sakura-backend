"""
Admin Authentication routes - separate from regular user auth
Uses the admins table instead of users table
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel

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
        
        # Create access token (valid for 8 hours for admins)
        access_token = create_access_token(
            data={"sub": admin.email, "admin_id": admin.id, "is_admin": True},
            expires_delta=timedelta(hours=8)
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
