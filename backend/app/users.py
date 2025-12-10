import os
import secrets
import hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

router = APIRouter(prefix="/api/users")


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password with salt using SHA-256. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify a password against stored hash and salt."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, stored_hash)


class Permissions(BaseModel):
    create: bool = False
    edit: bool = False
    delete: bool = False


class User(BaseModel):
    id: int
    username: str
    password_hash: str
    password_salt: str
    role: str
    permissions: Permissions

    # For backward compatibility, expose password check
    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash, self.password_salt)


class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    permissions: Permissions = Permissions()


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None
    permissions: Permissions | None = None


class UserResponse(BaseModel):
    """Safe user response without password fields."""
    id: int
    username: str
    role: str
    permissions: Permissions


_users: Dict[int, User] = {}
_counter = 1
_admin_created = False


def ensure_default_admin() -> None:
    """Insert the default admin user if none exist."""
    global _counter, _admin_created
    if _admin_created or _users:
        return  # Only create admin once

    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin")

    # Warn if using default credentials
    if username == "admin" and password == "admin":
        import logging
        logging.warning(
            "SECURITY WARNING: Using default admin credentials. "
            "Set ADMIN_USERNAME and ADMIN_PASSWORD environment variables for production."
        )

    password_hash, password_salt = hash_password(password)
    admin = User(
        id=_counter,
        username=username,
        password_hash=password_hash,
        password_salt=password_salt,
        role="admin",
        permissions=Permissions(create=True, edit=True, delete=True),
    )
    _users[_counter] = admin
    _counter += 1
    _admin_created = True


ensure_default_admin()


@router.get("/", response_model=List[UserResponse])
def list_users() -> List[UserResponse]:
    """List all users (without password fields)."""
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            role=u.role,
            permissions=u.permissions
        )
        for u in _users.values()
    ]


@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate) -> UserResponse:
    """Create a new user with hashed password."""
    global _counter

    # Check for duplicate username
    for existing in _users.values():
        if existing.username == user.username:
            raise HTTPException(status_code=400, detail="Username already exists")

    password_hash, password_salt = hash_password(user.password)
    new_user = User(
        id=_counter,
        username=user.username,
        password_hash=password_hash,
        password_salt=password_salt,
        role=user.role,
        permissions=user.permissions,
    )
    _users[_counter] = new_user
    _counter += 1
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        role=new_user.role,
        permissions=new_user.permissions
    )


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserUpdate) -> UserResponse:
    """Update a user. If password is provided, it will be hashed."""
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")

    stored = _users[user_id]
    update_data = user.dict(exclude_unset=True)

    # Hash password if provided
    if "password" in update_data and update_data["password"]:
        password_hash, password_salt = hash_password(update_data["password"])
        update_data["password_hash"] = password_hash
        update_data["password_salt"] = password_salt
        del update_data["password"]

    # Create updated user
    updated = stored.copy(update=update_data)
    _users[user_id] = updated
    return UserResponse(
        id=updated.id,
        username=updated.username,
        role=updated.role,
        permissions=updated.permissions
    )


@router.delete("/{user_id}")
def delete_user(user_id: int) -> Dict[str, str]:
    """Delete a user."""
    if user_id not in _users:
        raise HTTPException(status_code=404, detail="User not found")
    del _users[user_id]
    return {"status": "deleted"}
