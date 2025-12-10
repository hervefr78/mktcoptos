import os
import secrets
import time
import hmac
import hashlib
import json
import base64
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

from . import users

router = APIRouter(prefix="/api")

# JWT-like token configuration
# In production, use a proper secret from environment variable
JWT_SECRET = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
TOKEN_EXPIRY_SECONDS = int(os.getenv("TOKEN_EXPIRY_SECONDS", "86400"))  # 24 hours default

security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenPayload(BaseModel):
    user_id: int
    username: str
    role: str
    exp: int  # Expiration timestamp


def create_token(user_id: int, username: str, role: str) -> str:
    """Create a signed token with expiration."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
        "iat": int(time.time()),
    }
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()

    # Create signature
    signature = hmac.new(
        JWT_SECRET.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> Optional[TokenPayload]:
    """Verify token signature and expiration. Returns payload if valid."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, signature = parts

        # Verify signature
        expected_signature = hmac.new(
            JWT_SECRET.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(signature, expected_signature):
            return None

        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)

        # Check expiration
        if payload.get("exp", 0) < int(time.time()):
            return None

        return TokenPayload(**payload)
    except Exception:
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenPayload]:
    """Get current user from Authorization header. Returns None if not authenticated."""
    if not credentials:
        return None

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenPayload:
    """Require valid authentication. Raises 401 if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def require_admin(user: TokenPayload = Depends(require_auth)) -> TokenPayload:
    """Require admin role. Raises 403 if not admin."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/login")
def login(req: LoginRequest) -> dict:
    """Authenticate user and return signed token."""
    for user in users._users.values():
        if user.username == req.username and user.check_password(req.password):
            token = create_token(user.id, user.username, user.role)
            return {
                "token": token,
                "role": user.role,
                "expires_in": TOKEN_EXPIRY_SECONDS,
            }
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout")
def logout() -> dict:
    """Logout endpoint. Client should discard token."""
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(user: TokenPayload = Depends(require_auth)) -> dict:
    """Get current authenticated user info."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
    }


@router.post("/refresh")
async def refresh_token(user: TokenPayload = Depends(require_auth)) -> dict:
    """Refresh the current token."""
    new_token = create_token(user.user_id, user.username, user.role)
    return {
        "token": new_token,
        "expires_in": TOKEN_EXPIRY_SECONDS,
    }
