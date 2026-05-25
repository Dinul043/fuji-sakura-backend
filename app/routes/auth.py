"""
Authentication routes for user registration, login, and OTP verification
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid, os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.models.user import User
from app.models.user_token import UserToken
from app.utils.security import verify_password, get_password_hash, create_access_token
from app.utils.security import get_current_user as get_current_user_from_auth
from app.utils.email import send_otp_email, send_password_reset_email
from app.utils.otp import generate_otp, generate_reset_token, is_otp_expired, get_otp_expiry, get_reset_token_expiry

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models for request/response
class UserSignup(BaseModel):
    email: str  # Temporarily changed from EmailStr to debug
    firstName: str
    lastName: str
    password: str

class UserLogin(BaseModel):
    email: str  # Temporarily changed from EmailStr to debug
    password: str
    rememberMe: bool = False  # Optional field for extended session

class OTPVerification(BaseModel):
    email: str  # Temporarily changed from EmailStr to debug
    otp: str

class ForgotPassword(BaseModel):
    email: str  # Temporarily changed from EmailStr to debug

class ResetCodeVerification(BaseModel):
    email: str  # Temporarily changed from EmailStr to debug
    token: str

class ResetPassword(BaseModel):
    email: str  # Temporarily changed from EmailStr to debug
    token: str
    newPassword: str

class UpdateUserDetails(BaseModel):
    email: str
    firstName: str
    lastName: str = ""  # optional
    password: str
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    is_verified: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Helper functions
def validate_password(password: str) -> tuple[bool, str]:
    """Validate password meets requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        return False, "Password must contain at least 1 uppercase, 1 lowercase, and 1 number"
    
    return True, ""

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    logger.info(f"🔍 SEARCHING FOR USER WITH EMAIL: '{email}'")
    user = db.query(User).filter(User.email == email).first()
    if user:
        logger.info(f"✅ FOUND USER: ID={user.id}, EMAIL='{user.email}'")
    else:
        logger.warning(f"❌ NO USER FOUND FOR EMAIL: '{email}'")
    return user

def get_or_create_user_token(db: Session, user_id: int) -> UserToken:
    """Get existing token or create new one for user"""
    token = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    if not token:
        token = UserToken(user_id=user_id)
        db.add(token)
        db.commit()
        db.refresh(token)
    return token

def clear_user_tokens(db: Session, user_id: int):
    """Clear all tokens for a user"""
    db.query(UserToken).filter(UserToken.user_id == user_id).delete()
    db.commit()

def cleanup_old_unverified_users(db: Session):
    """
    Clean up unverified users older than 7 days (optional cleanup)
    This prevents database bloat from incomplete signups
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        old_unverified = db.query(User).filter(
            User.is_verified == False,
            User.created_at < cutoff_date.replace(tzinfo=None)
        ).all()
        
        for user in old_unverified:
            # Delete associated tokens first
            db.query(UserToken).filter(UserToken.user_id == user.id).delete()
            # Delete user
            db.delete(user)
            logger.info(f"🧹 Cleaned up old unverified user: {user.email}")
        
        if old_unverified:
            db.commit()
            logger.info(f"🧹 Cleaned up {len(old_unverified)} old unverified users")
            
    except Exception as e:
        logger.error(f"❌ Cleanup error: {str(e)}")
        db.rollback()

# Authentication routes
@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    User signup with email OTP verification
    """
    try:
        # Debug: Log the received email
        logger.info(f"🔍 RECEIVED EMAIL: '{user_data.email}' (length: {len(user_data.email)})")
        logger.info(f"🔍 EMAIL REPR: {repr(user_data.email)}")
        
        # Check if user already exists
        existing_user = get_user_by_email(db, user_data.email)
        
        if existing_user:
            if existing_user.is_verified:
                # User is fully registered and verified - don't allow duplicate
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already registered. Please use Sign In to access your account."
                )
            else:
                # User exists but not verified (incomplete signup) - allow re-signup
                # This handles the case where user got OTP but didn't complete verification
                logger.info(f"🔄 Re-signup attempt for unverified user: {user_data.email}")
                
                # Validate new password
                is_valid, error_msg = validate_password(user_data.password.strip())
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )
                
                # Update user data with new information (user might want to change name/password)
                full_name = f"{user_data.firstName} {user_data.lastName}".strip()
                existing_user.name = full_name
                existing_user.password = get_password_hash(user_data.password.strip())
                existing_user.updated_at = datetime.now()
                
                # Generate new OTP (clear any old OTP)
                token = get_or_create_user_token(db, existing_user.id)
                token.otp = generate_otp()
                token.otp_expires_at = get_otp_expiry()
                # Clear any old reset tokens
                token.reset_token = None
                token.reset_token_expires_at = None
                
                db.commit()
                
                # Send new OTP email
                email_sent = send_otp_email(
                    to_email=user_data.email,
                    otp=token.otp,
                    user_name=full_name
                )
                
                logger.info(f"🔐 NEW OTP for existing unverified user {user_data.email}: {token.otp}")
                
                return {
                    "message": "New OTP sent! Please verify your email to complete registration.",
                    "email": user_data.email,
                    "requires_verification": True,
                    "email_sent": email_sent
                }
        
        # Validate password
        is_valid, error_msg = validate_password(user_data.password.strip())
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Create new user
        full_name = f"{user_data.firstName} {user_data.lastName}".strip()
        hashed_password = get_password_hash(user_data.password.strip())
        otp = generate_otp()
        
        new_user = User(
            email=user_data.email,
            name=full_name,
            password=hashed_password,
            is_verified=False,
            is_active=True
        )
        
        db.add(new_user)
        try:
            db.commit()
            db.refresh(new_user)
        except Exception as db_error:
            db.rollback()
            if "Duplicate entry" in str(db_error) or "UNIQUE constraint" in str(db_error):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already registered. Please try with a different email or use Sign In if you have an account."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database error occurred. Please try again."
                )
        
        # Create token record
        token = UserToken(
            user_id=new_user.id,
            otp=otp,
            otp_expires_at=get_otp_expiry()
        )
        
        db.add(token)
        db.commit()
        
        # Send OTP email
        email_sent = send_otp_email(
            to_email=user_data.email,
            otp=otp,
            user_name=full_name
        )
        
        logger.info(f"🔐 NEW USER OTP for {user_data.email}: {otp}")
        
        return {
            "message": "Signup successful! Please verify your email with the OTP sent.",
            "email": user_data.email,
            "requires_verification": True,
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Signup error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup error: {str(e)}"
        )

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(otp_data: OTPVerification, db: Session = Depends(get_db)):
    """
    Verify OTP and activate user account
    """
    try:
        # Debug: Log the received email for OTP verification
        logger.info(f"🔍 OTP VERIFICATION - RECEIVED EMAIL: '{otp_data.email}' (length: {len(otp_data.email)})")
        logger.info(f"🔍 OTP VERIFICATION - EMAIL REPR: {repr(otp_data.email)}")
        logger.info(f"🔍 OTP VERIFICATION - RECEIVED OTP: '{otp_data.otp}'")
        
        # Get user and their token
        user = get_user_by_email(db, otp_data.email)
        if not user:
            logger.warning(f"❌ User not found for email: '{otp_data.email}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user's token
        token = db.query(UserToken).filter(UserToken.user_id == user.id).first()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OTP found. Please request a new one."
            )
        
        # Check if already verified
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified. Please login."
            )
        
        # Check if OTP exists
        if not token.otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP not found or expired. Please request a new one."
            )
        
        # Check if OTP expired
        if is_otp_expired(token.otp_expires_at):
            # Clear expired token
            clear_user_tokens(db, user.id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired. Please request a new one."
            )
        
        # Verify OTP
        if token.otp != otp_data.otp:
            logger.warning(f"❌ Invalid OTP attempt for {otp_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP"
            )
        
        # OTP verified - activate account and clear tokens
        user.is_verified = True
        user.last_login = datetime.now()
        user.updated_at = datetime.now()
        
        # Clear all tokens for this user (OTP no longer needed)
        clear_user_tokens(db, user.id)
        
        db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        logger.info(f"✅ OTP verified successfully for {otp_data.email} - Tokens cleared")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_verified": user.is_verified
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OTP verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OTP verification"
        )

@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    User login with email and password
    """
    try:
        # Get user
        user = get_user_by_email(db, login_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password.strip(), user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Check if email is verified
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email first. Check your inbox for OTP."
            )
        
        # Update last login (but don't update updated_at for just login)
        user.last_login = datetime.now()
        # Note: updated_at should only change when profile data changes
        db.commit()
        
        # Access token: 1 hour (refresh token handles session persistence)
        access_token = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=timedelta(hours=1)
        )

        # Refresh token: long-lived based on rememberMe
        from app.utils.security import create_refresh_token_for_entity
        refresh_expires = timedelta(days=30) if login_data.rememberMe else timedelta(days=1)
        refresh_token = create_refresh_token_for_entity(
            entity_id=user.id, role="user", db=db, expires_delta=refresh_expires
        )

        logger.info(f"✅ User logged in successfully: {login_data.email}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_verified": user.is_verified
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.post("/resend-otp")
def resend_otp(email_data: ForgotPassword, db: Session = Depends(get_db)):
    """
    Resend OTP for unverified users
    """
    try:
        user = get_user_by_email(db, email_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified. Please login."
            )
        
        # Generate new OTP
        otp = generate_otp()
        token = get_or_create_user_token(db, user.id)
        token.otp = otp
        token.otp_expires_at = get_otp_expiry()
        db.commit()
        
        # Send email
        email_sent = send_otp_email(
            to_email=email_data.email,
            otp=otp,
            user_name=user.name
        )
        
        logger.info(f"🔐 RESEND OTP for {email_data.email}: {otp}")
        
        return {
            "message": "OTP resent successfully",
            "email_sent": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resend OTP error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OTP resend"
        )

@router.post("/forgot-password")
def forgot_password(email_data: ForgotPassword, db: Session = Depends(get_db)):
    """
    Send password reset token via email
    """
    try:
        user = get_user_by_email(db, email_data.email)
        if not user:
            # Don't reveal if email exists (security best practice)
            return {"message": "If this email exists, a password reset link has been sent."}
        
        # Generate reset token
        reset_token = generate_reset_token()
        
        # Get or create token record for this user
        token = get_or_create_user_token(db, user.id)
        token.reset_token = reset_token
        token.reset_token_expires_at = get_reset_token_expiry()
        db.commit()
        
        # Send reset email
        email_sent = send_password_reset_email(
            to_email=email_data.email,
            reset_token=reset_token,
            user_name=user.name
        )
        
        logger.info(f"🔑 Password reset token for {email_data.email}: {reset_token}")
        
        return {
            "message": "If this email exists, a password reset link has been sent.",
            "email_sent": email_sent
        }
        
    except Exception as e:
        logger.error(f"❌ Forgot password error: {str(e)}")
        return {"message": "If this email exists, a password reset link has been sent."}

@router.post("/verify-reset-code")
def verify_reset_code(reset_data: ResetCodeVerification, db: Session = Depends(get_db)):
    """
    Verify reset code without changing password
    """
    try:
        user = get_user_by_email(db, reset_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user's token record
        token = db.query(UserToken).filter(UserToken.user_id == user.id).first()
        if not token or not token.reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No reset token found. Please request a new password reset."
            )
        
        # Check if token expired
        if is_otp_expired(token.reset_token_expires_at):
            # Clear expired token
            clear_user_tokens(db, user.id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset code expired. Please request a new password reset."
            )
        
        # Verify token
        if token.reset_token != reset_data.token:
            logger.warning(f"❌ Invalid reset code attempt for {reset_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset code. Please check the code from your email."
            )
        
        logger.info(f"✅ Reset code verified successfully for {reset_data.email}")
        
        return {"message": "Reset code verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Reset code verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during reset code verification"
        )

@router.post("/reset-password")
def reset_password(reset_data: ResetPassword, db: Session = Depends(get_db)):
    """
    Reset password with token
    """
    try:
        user = get_user_by_email(db, reset_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user's token record
        token = db.query(UserToken).filter(UserToken.user_id == user.id).first()
        if not token or not token.reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No reset token found. Please request a new password reset."
            )
        
        # Check if token expired
        if is_otp_expired(token.reset_token_expires_at):
            # Clear expired token
            clear_user_tokens(db, user.id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token expired. Please request a new password reset."
            )
        
        # Verify token
        if token.reset_token != reset_data.token:
            logger.warning(f"❌ Invalid reset token attempt for {reset_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset code. Please check the code from your email."
            )
        
        # Validate new password
        is_valid, error_msg = validate_password(reset_data.newPassword.strip())
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Check if new password is same as current password
        if verify_password(reset_data.newPassword.strip(), user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be the same as your current password. Please choose a different password."
            )
        
        # Update password and clear reset tokens
        user.password = get_password_hash(reset_data.newPassword.strip())
        user.updated_at = datetime.now()
        
        # Clear all tokens for this user
        clear_user_tokens(db, user.id)
        
        db.commit()
        
        logger.info(f"✅ Password reset successful for {reset_data.email}")
        
        return {"message": "Password reset successful. You can now login with your new password."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password reset"
        )

@router.put("/update-user-details")
def update_user_details(user_data: UpdateUserDetails, db: Session = Depends(get_db)):
    """
    Update user details after OTP verification
    """
    try:
        # Get user
        user = get_user_by_email(db, user_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is verified (OTP should be verified first)
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please verify your email first"
            )
        
        # Validate password
        is_valid, error_msg = validate_password(user_data.password.strip())
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Update user details
        full_name = f"{user_data.firstName} {user_data.lastName}".strip()
        user.name = full_name
        user.password = get_password_hash(user_data.password.strip())
        if user_data.phone:
            user.phone = user_data.phone.strip()
        user.updated_at = datetime.now()
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ User details updated successfully for {user_data.email}")
        
        return {
            "message": "User details updated successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_verified": user.is_verified
            }
        }
        
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update user details error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user details update"
        )

class UpdateProfileRequest(BaseModel):
    name: str
    phone: str | None = None
    address: str | None = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.get("/me")
def get_profile(
    current_user: User = Depends(get_current_user_from_auth),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "address": current_user.address,
        "profile_image": current_user.profile_image,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }

@router.put("/me")
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user_from_auth),
    db: Session = Depends(get_db)
):
    """Update user name, phone, address"""
    current_user.name = data.name.strip()
    if data.phone is not None:
        current_user.phone = data.phone.strip() or None
    if data.address is not None:
        current_user.address = data.address.strip() or None
    current_user.updated_at = datetime.now()
    db.commit()
    return {
        "message": "Profile updated successfully",
        "name": current_user.name,
        "phone": current_user.phone,
        "address": current_user.address,
    }

@router.put("/me/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_from_auth),
    db: Session = Depends(get_db)
):
    """Change user password"""
    if not verify_password(data.current_password.strip(), current_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    is_valid, error_msg = validate_password(data.new_password.strip())
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    if verify_password(data.new_password.strip(), current_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password cannot be the same as current password")

    current_user.password = get_password_hash(data.new_password.strip())
    current_user.updated_at = datetime.now()
    db.commit()
    return {"message": "Password changed successfully"}

@router.post("/me/upload-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_auth),
    db: Session = Depends(get_db)
):
    """Upload user profile image - same pattern as restaurant/menu images"""
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")

    # Delete old image file from disk if exists
    if current_user.profile_image:
        old_path = current_user.profile_image.lstrip("/")
        if os.path.exists(old_path):
            os.remove(old_path)

    # Save new image - same naming pattern as menu/restaurant
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    unique_filename = f"user_{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
    upload_dir = Path("uploads/profile_images")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / unique_filename

    file_content = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_content)

    # Store relative URL in DB - same as image_url in menu/restaurant
    image_url = f"/uploads/profile_images/{unique_filename}"
    current_user.profile_image = image_url
    current_user.updated_at = datetime.now()
    db.commit()

    return {"profile_image": image_url}


# ── Refresh Token Endpoint ─────────────────────────────────────────────────

class UserRefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
def user_refresh_token(data: UserRefreshRequest, db: Session = Depends(get_db)):
    """Exchange valid refresh token for new access + refresh token pair."""
    from app.utils.security import verify_refresh_token_from_db, create_refresh_token_for_entity

    record = verify_refresh_token_from_db(data.refresh_token, role="user", db=db)

    user = db.query(User).filter(User.id == record.entity_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    # New access token — always 1 hour
    new_access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(hours=1)
    )

    # Calculate refresh token expiry — same duration as the original
    # (preserves the remember me choice from login)
    original_duration = record.expires_at - record.created_at
    # Clamp: min 1 day, max 30 days
    if original_duration.total_seconds() < 86400:
        refresh_expires = timedelta(days=1)
    elif original_duration.total_seconds() > 30 * 86400:
        refresh_expires = timedelta(days=30)
    else:
        refresh_expires = original_duration

    # Rotate refresh token — revoke old, issue new
    record.revoked = True
    db.commit()
    new_refresh_token = create_refresh_token_for_entity(
        entity_id=user.id, role="user", db=db, expires_delta=refresh_expires
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def user_logout(data: UserRefreshRequest, db: Session = Depends(get_db)):
    """Revoke refresh token on logout."""
    from app.utils.security import revoke_refresh_token_in_db
    revoke_refresh_token_in_db(data.refresh_token, role="user", db=db)
    return {"message": "Logged out successfully"}
