"""
OTP generation and validation utilities
"""

import random
import string
from datetime import datetime, timedelta
from app.core.config import settings

def generate_otp() -> str:
    """Generate 4-digit OTP"""
    return ''.join(random.choices(string.digits, k=4))

def generate_reset_token() -> str:
    """Generate 4-digit reset token"""
    return ''.join(random.choices(string.digits, k=4))

def is_otp_expired(expires_at: datetime) -> bool:
    """Check if OTP has expired"""
    return datetime.utcnow() > expires_at

def get_otp_expiry() -> datetime:
    """Get OTP expiry time (10 minutes from now)"""
    return datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

def get_reset_token_expiry() -> datetime:
    """Get reset token expiry time (30 minutes from now)"""
    return datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)