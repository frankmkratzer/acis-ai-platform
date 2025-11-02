"""
Authentication Router - Secure authentication with bcrypt password hashing

Uses environment variables for credentials and JWT configuration.
Passwords are hashed using bcrypt for security.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import JWTError, jwt

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Security
security = HTTPBasic()

# Configuration from environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))

# Admin credentials from environment
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@acis-ai.com")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")  # bcrypt hash

if not ADMIN_PASSWORD_HASH:
    print("WARNING: ADMIN_PASSWORD_HASH not set in environment variables!")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt hashing"""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/login")
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Simple login endpoint using HTTP Basic Auth

    For now: Just checks against hardcoded admin credentials
    Later: Can add proper user management with database

    Returns JWT token
    """
    # Check credentials
    if credentials.username != ADMIN_EMAIL or not verify_password(
        credentials.password, ADMIN_PASSWORD_HASH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.username}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": ADMIN_EMAIL,
        "role": "admin",
    }


@router.get("/me")
async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Get current user info"""
    if credentials.username != ADMIN_EMAIL or not verify_password(
        credentials.password, ADMIN_PASSWORD_HASH
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return {"email": ADMIN_EMAIL, "role": "admin", "is_active": True}


@router.get("/health")
async def health_check():
    """Health check endpoint (no auth required)"""
    return {"status": "ok", "service": "auth"}
