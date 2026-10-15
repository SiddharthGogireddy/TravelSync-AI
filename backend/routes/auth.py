import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query, Request, status
from pydantic import BaseModel, Field

from backend.services.auth.jwt_service import (
    create_access_token,
    verify_access_token,
    get_auth_config,
    is_auth_dev_mode,
    AUTH_DEV_MODE,
    JWT_EXPIRATION_SECONDS,
)
from backend.services.auth.user_store import (
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile
    expires_in: int


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 characters)")
    full_name: Optional[str] = Field(default=None, max_length=128, description="User display name")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


class ClaimSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128, description="Existing session user_id to claim")
    email: str = Field(..., min_length=5, max_length=255, description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 characters)")
    full_name: Optional[str] = Field(default=None, max_length=128, description="User display name")


class TokenRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128, description="User identifier to issue token for")
    email: Optional[str] = Field(default=None, description="Optional user email")
    role: Optional[str] = Field(default="user", description="Optional user role")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    expires_in: int


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    """
    Registers a new user account with email and password in production and dev modes.
    Issues a cryptographically signed JWT upon successful account creation.
    """
    try:
        user = create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
    )

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(**user),
        expires_in=JWT_EXPIRATION_SECONDS,
    )


@router.post("/claim-session", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def claim_session(payload: ClaimSessionRequest):
    """
    Attaches an email and password credential to an existing user session ID.
    Preserves all existing trip ownership, collaborator roles, and preferences without data mutation.
    """
    clean_uid = payload.user_id.strip()
    if not clean_uid:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        user = create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            user_id=clean_uid,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
    )

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(**user),
        expires_in=JWT_EXPIRATION_SECONDS,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    """
    Authenticates a user via email and password in production and dev modes.
    Returns a cryptographically signed JWT access token.
    """
    user = authenticate_user(email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
    )

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfile(**user),
        expires_in=JWT_EXPIRATION_SECONDS,
    )


@router.post("/token", response_model=TokenResponse)
def issue_token(payload: TokenRequest):
    """
    Issues a cryptographically signed JWT for development, testing, and client authentication.
    Permitted only when AUTH_DEV_MODE is explicitly enabled.
    """
    if not is_auth_dev_mode():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development token issuance is disabled in production mode. Please authenticate via /auth/login or /auth/register.",
        )

    clean_user = payload.user_id.strip()
    if not clean_user:
        raise HTTPException(status_code=400, detail="user_id cannot be blank")

    token = create_access_token(
        user_id=clean_user,
        email=payload.email,
        role=payload.role,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=clean_user,
        expires_in=JWT_EXPIRATION_SECONDS,
    )


@router.get("/me")
def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    token: Optional[str] = Query(None),
):
    """
    Returns verified identity information derived exclusively from cryptographic credentials.
    """
    raw_token = None
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
    elif token:
        raw_token = token.strip()
    elif request:
        auth_hdr = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_hdr and auth_hdr.lower().startswith("bearer "):
            raw_token = auth_hdr[7:].strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Bearer token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = verify_access_token(raw_token)
    uid = claims.get("sub")
    db_user = get_user_by_id(uid) if uid else None
    return {
        "authenticated": True,
        "user_id": uid,
        "email": claims.get("email") or (db_user["email"] if db_user else None),
        "full_name": db_user.get("full_name") if db_user else None,
        "role": claims.get("role", "user"),
        "issuer": claims.get("iss"),
        "expires_at": claims.get("exp"),
    }


@router.get("/config")
def get_configuration():
    """
    Returns public auth configuration without disclosing secrets.
    """
    return get_auth_config()
