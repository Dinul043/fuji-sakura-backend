"""
Security utilities for password hashing and JWT tokens
"""


from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

# Password hashing context with compatible bcrypt version
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Password hashing error: {e}")
        raise ValueError("Failed to hash password")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # This automatically extracts the JWT token from the request header
    db: Session = Depends(get_db)
):
    """Get current user from JWT token"""
    from app.models.user import User  # Import here to avoid circular imports
 
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)  # Decode and verify the token
        if payload is None:
            raise credentials_exception
        
        user_id_str: str = payload.get("sub")  # Store user ID inside the token (sub) so we don't need extra DB lookups
        if user_id_str is None:
            raise credentials_exception

        user_id = int(user_id_str)
            
    except (JWTError, ValueError):
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()  # Fetch the authenticated user from database
    if user is None:
        raise credentials_exception
    
    return user

    


# ── Refresh Token Utilities ────────────────────────────────────────────────

def create_refresh_token_for_entity(entity_id: int, role: str, db, expires_delta) -> str:
    """
    Generate a secure refresh token, hash it, store in DB.
    Revokes any existing active tokens for this entity+role (single session).
    Returns the RAW token (sent to client).
    """
    from app.models.refresh_token import RefreshToken
    from datetime import datetime

    raw_token = RefreshToken.generate()
    token_hash = RefreshToken.hash_token(raw_token)
    expires_at = datetime.now() + expires_delta

    # Revoke existing tokens for this entity+role
    db.query(RefreshToken).filter(
        RefreshToken.entity_id == entity_id,
        RefreshToken.role == role,
        RefreshToken.revoked == False
    ).update({"revoked": True})

    # Store new hashed token
    refresh = RefreshToken(
        entity_id=entity_id,
        role=role,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(refresh)
    db.commit()

    return raw_token


def verify_refresh_token_from_db(raw_token: str, role: str, db):
    """
    Verify a refresh token. Returns the DB record if valid.
    Raises HTTPException if invalid/expired/revoked.
    """
    from app.models.refresh_token import RefreshToken
    from datetime import datetime

    token_hash = RefreshToken.hash_token(raw_token)
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.role == role
    ).first()

    if not record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if record.revoked:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    if datetime.now() >= record.expires_at:
        raise HTTPException(status_code=401, detail="Refresh token has expired")

    return record


def revoke_refresh_token_in_db(raw_token: str, role: str, db) -> bool:
    """Revoke a specific refresh token on logout."""
    from app.models.refresh_token import RefreshToken

    token_hash = RefreshToken.hash_token(raw_token)
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.role == role
    ).first()

    if record:
        record.revoked = True
        db.commit()
        return True
    return False
