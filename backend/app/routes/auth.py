"""Authentication routes."""

from datetime import datetime, timedelta
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    PasswordChangeRequest,
    PasswordChangeResponse,
    SignupRequest,
    SignupConfigResponse,
    PasswordPolicyResponse,
)
from app.services.auth import authenticate_user, create_token_response
from app.services.audit import log_audit_event
from app.utils.security import decode_access_token
from app.models.user import User
from app.models.system_preferences import SystemPreferences
from sqlalchemy import select
from app.utils.security import verify_password, hash_password
from app.utils.password_policy import validate_password_policy, validate_username
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)
SESSION_SEEN_UPDATE_SECONDS = 60


async def _get_system_preferences(db: AsyncSession) -> SystemPreferences:
    result = await db.execute(select(SystemPreferences).where(SystemPreferences.id == 1))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = SystemPreferences(
            id=1,
            session_timeout_minutes=30,
            # Allow existing tokens to validate until an admin resets sessions.
            auth_token_not_before=None,
            allow_self_signup=False,
            require_signup_verification=False,
            require_signup_captcha=True,
            signup_captcha_provider="turnstile",
            signup_captcha_site_key=None,
            password_min_length=12,
            password_require_uppercase=True,
            password_require_lowercase=True,
            password_require_number=True,
            password_require_special=False,
        )
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


async def _verify_turnstile(token: str, request: Request) -> None:
    if not settings.turnstile_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Signup CAPTCHA is misconfigured. Contact an administrator.",
        )

    data = {"secret": settings.turnstile_secret_key, "response": token}
    if request.client and request.client.host:
        data["remoteip"] = request.client.host

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data=data,
            )
    except Exception as exc:  # pragma: no cover - network failure path
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CAPTCHA verification temporarily unavailable.",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed.",
        )

    result = response.json()
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed.",
        )


def _password_policy_payload(prefs: SystemPreferences) -> PasswordPolicyResponse:
    return PasswordPolicyResponse(
        min_length=prefs.password_min_length,
        require_uppercase=prefs.password_require_uppercase,
        require_lowercase=prefs.password_require_lowercase,
        require_number=prefs.password_require_number,
        require_special=prefs.password_require_special,
    )


@router.get("/signup/config", response_model=SignupConfigResponse)
async def get_signup_config(db: AsyncSession = Depends(get_db)):
    prefs = await _get_system_preferences(db)
    return SignupConfigResponse(
        allow_self_signup=prefs.allow_self_signup,
        require_email_verification=prefs.require_signup_verification,
        require_signup_captcha=prefs.require_signup_captcha,
        signup_captcha_provider=prefs.signup_captcha_provider,
        signup_captcha_site_key=prefs.signup_captcha_site_key,
        password_policy=_password_policy_payload(prefs),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT token.

    Args:
        credentials: Login credentials (email or admin username and password)
        db: Database session

    Returns:
        TokenResponse with access token

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = await authenticate_user(
        db,
        credentials.email,
        credentials.password,
        include_disabled=True,
    )

    if not user:
        await log_audit_event(
            db,
            action="auth.login_failed",
            actor=None,
            target_type="user",
            target_id=credentials.email,
            metadata={"identifier": credentials.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if user.is_disabled:
        await log_audit_event(
            db,
            action="auth.login_disabled",
            actor=None,
            target_type="user",
            target_id=str(user.id),
            metadata={"identifier": credentials.email},
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    now = datetime.utcnow()
    user.last_login_at = now
    user.last_seen_at = now
    prefs = await _get_system_preferences(db)
    policy_errors = validate_password_policy(credentials.password, prefs)
    if policy_errors:
        user.force_password_reset = True
    await db.commit()
    await log_audit_event(
        db,
        action="auth.login_success",
        actor=user,
        target_type="user",
        target_id=str(user.id),
        metadata={"identifier": credentials.email},
        request=request,
    )

    expires_minutes = prefs.session_timeout_minutes or 30
    return create_token_response(user, expires_minutes=expires_minutes)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_system_preferences(db)
    if not prefs.allow_self_signup:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-service signup is disabled by the administrator.",
        )

    username_error = validate_username(payload.username)
    if username_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=username_error)

    normalized_username = payload.username.strip()
    normalized_email = payload.email.strip().lower()

    # Enforce uniqueness
    existing_username = await db.execute(select(User).where(User.username == normalized_username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already in use."
        )

    existing_email = await db.execute(select(User).where(User.email == normalized_email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered."
        )

    if prefs.require_signup_captcha:
        if not payload.captcha_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="CAPTCHA token is required."
            )
        if prefs.signup_captcha_provider == "turnstile":
            await _verify_turnstile(payload.captcha_token, request)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported CAPTCHA provider."
            )

    policy_errors = validate_password_policy(payload.password, prefs)
    if policy_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_errors[0])

    new_user = User(
        username=normalized_username,
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        is_admin=False,
        is_disabled=False,
        force_password_reset=False,
        is_email_verified=not prefs.require_signup_verification,
        last_login_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await log_audit_event(
        db,
        action="auth.signup_success",
        actor=new_user,
        target_type="user",
        target_id=str(new_user.id),
        metadata={"email": normalized_email},
        request=request,
    )

    expires_minutes = prefs.session_timeout_minutes or 30
    return create_token_response(new_user, expires_minutes=expires_minutes)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token: str | None = Query(None, description="JWT bearer token (optional)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    bearer = credentials.credentials if credentials else token
    if not bearer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization header missing",
        )

    # Decode token
    payload = decode_access_token(bearer)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Get user from database
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if user.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    prefs = await _get_system_preferences(db)
    iat = payload.get("iat")
    if prefs.auth_token_not_before:
        if iat is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )
        not_before_ts = int(prefs.auth_token_not_before.timestamp())
        if int(iat) <= not_before_ts:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )

    timeout_minutes = prefs.session_timeout_minutes or 30
    timeout_window = timedelta(minutes=timeout_minutes)
    last_seen = user.last_seen_at or user.last_login_at
    if user.last_login_at and (not last_seen or user.last_login_at > last_seen):
        last_seen = user.last_login_at
    now = datetime.utcnow()
    if last_seen and now - last_seen > timeout_window:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session timed out. Please log in again.",
        )

    if (
        user.last_seen_at is None
        or (now - user.last_seen_at).total_seconds() > SESSION_SEEN_UPDATE_SECONDS
    ):
        user.last_seen_at = now
        await db.commit()

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        UserResponse with user information
    """
    return UserResponse.model_validate(current_user)


@router.put("/password", response_model=PasswordChangeResponse)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password after verifying current password and confirmation.

    Raises:
        HTTPException: 400 if confirmation mismatch
        HTTPException: 401 if current password invalid
    """
    # Confirm match
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Verify current password
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Reject reuse
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400, detail="New password must differ from current password"
        )

    prefs = await _get_system_preferences(db)
    policy_errors = validate_password_policy(payload.new_password, prefs)
    if policy_errors:
        raise HTTPException(status_code=400, detail=policy_errors[0])

    # Update hash
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.force_password_reset = False
    await db.commit()
    await db.refresh(current_user)

    return PasswordChangeResponse(detail="Password changed successfully")


@router.post("/reset-sessions", status_code=status.HTTP_204_NO_CONTENT)
async def reset_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force-invalidate all sessions by bumping auth_token_not_before.

    Requires admin. Does not touch jobs; only login tokens are invalidated.
    """

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins may reset sessions.",
        )

    prefs = await _get_system_preferences(db)
    prefs.auth_token_not_before = datetime.utcnow()
    await db.commit()

    await log_audit_event(
        db,
        action="auth.sessions_reset",
        actor=current_user,
        target_type="system",
        target_id="system_preferences",
        metadata={"reason": "manual_reset"},
        request=request,
    )
