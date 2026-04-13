from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import resolve_active_username
from app.core.auth import create_access_token, generate_password_salt, hash_password, verify_password
from app.core.config import settings
from app.db.models.entities import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_user_with_password(db: Session, username: str, password: str) -> User:
    salt = generate_password_salt()
    password_hash = hash_password(password, salt)

    created = User(username=username, password_salt=salt, password_hash=password_hash)
    db.add(created)
    db.commit()
    db.refresh(created)
    return created


def _register_user(db: Session, username: str, password: str) -> User:
    existing = db.scalar(select(User).where(User.username == username))
    if existing is None:
        return _create_user_with_password(db, username, password)

    if existing.password_hash and existing.password_salt:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    # Legacy user rows from before password support can be upgraded in-place.
    existing.password_salt = generate_password_salt()
    existing.password_hash = hash_password(password, existing.password_salt)
    db.commit()
    db.refresh(existing)
    return existing


def _get_or_create_user(db: Session, username: str, password: str) -> User:
    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        if existing.password_hash and existing.password_salt:
            if not verify_password(password, existing.password_salt, existing.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
            return existing

        # Backward-compatible bootstrap for legacy users created before password support.
        existing.password_salt = generate_password_salt()
        existing.password_hash = hash_password(password, existing.password_salt)
        db.commit()
        db.refresh(existing)
        return existing

    return _create_user_with_password(db, username, password)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = _get_or_create_user(db, payload.username, payload.password)
    token = create_access_token(user.username)

    return LoginResponse(
        access_token=token,
        username=user.username,
        expires_in_seconds=settings.auth_token_ttl_hours * 3600,
    )


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = _register_user(db, payload.username, payload.password)
    token = create_access_token(user.username)

    return LoginResponse(
        access_token=token,
        username=user.username,
        expires_in_seconds=settings.auth_token_ttl_hours * 3600,
    )


@router.get("/me", response_model=MeResponse)
def me(username: str = Depends(resolve_active_username)) -> MeResponse:
    return MeResponse(username=username)
