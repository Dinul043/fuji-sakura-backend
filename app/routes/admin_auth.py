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