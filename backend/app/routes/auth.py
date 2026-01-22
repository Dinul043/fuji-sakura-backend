"""
Authentication routes for user registration, login, and OTP verification
"""

import logging
from datetime import datetime, timedelta, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.models.user import User
from app.models.user_token import UserToken
from app.utils.security import verify_password, get_password_hash, create_access_token
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
    email: str  # Temporarily changed from EmailStr to debug
    firstName: str
    lastName: str
    password: str

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
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This email is already registered. Please try with a different email or use Sign In if you have an account."
                )
            else:
                # User exists but not verified - resend OTP
                is_valid, error_msg = validate_password(user_data.password)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )
                
                # Update user data and generate new OTP
                full_name = f"{user_data.firstName} {user_data.lastName}".strip()
                existing_user.name = full_name
                existing_user.password = get_password_hash(user_data.password)
                
                # Get or create token record
                token = get_or_create_user_token(db, existing_user.id)
                token.otp = generate_otp()
                token.otp_expires_at = get_otp_expiry()
                
                db.commit()
                
                # Send OTP email
                email_sent = send_otp_email(
                    to_email=user_data.email,
                    otp=token.otp,
                    user_name=full_name
                )
                
                logger.info(f"🔐 RESEND OTP for {user_data.email}: {token.otp}")
                
                return {
                    "message": "Account exists but not verified. New OTP sent to your email.",
                    "email": user_data.email,
                    "requires_verification": True,
                    "email_sent": email_sent
                }
        
        # Validate password
        is_valid, error_msg = validate_password(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Create new user
        full_name = f"{user_data.firstName} {user_data.lastName}".strip()
        hashed_password = get_password_hash(user_data.password)
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
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()  # Explicitly set updated_at
        
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
        if not verify_password(login_data.password, user.password):
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
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()  # Explicitly set updated_at
        db.commit()
        
        # Create access token with appropriate expiry
        if login_data.rememberMe:
            # Extended session: 30 days
            expires_delta = timedelta(days=30)
            logger.info(f"🔒 Extended session (30 days) for {login_data.email}")
        else:
            # Short session: 1 day
            expires_delta = timedelta(days=1)
            logger.info(f"🔒 Short session (1 day) for {login_data.email}")
            
        access_token = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=expires_delta
        )
        
        logger.info(f"✅ User logged in successfully: {login_data.email}")
        
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
        is_valid, error_msg = validate_password(reset_data.newPassword)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Check if new password is same as current password
        if verify_password(reset_data.newPassword, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be the same as your current password. Please choose a different password."
            )
        
        # Update password and clear reset tokens
        user.password = get_password_hash(reset_data.newPassword)
        user.updated_at = datetime.utcnow()
        
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
        is_valid, error_msg = validate_password(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Update user details
        full_name = f"{user_data.firstName} {user_data.lastName}".strip()
        user.name = full_name
        user.password = get_password_hash(user_data.password)
        user.updated_at = datetime.utcnow()
        
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