import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Query, Request, status
from pydantic import BaseModel, Field

from backend.services.auth.jwt_service import (
    create_access_token,
    verify_access_token,
    get_auth_config,
    AUTH_DEV_MODE,
    JWT_EXPIRATION_SECONDS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128, description="User identifier to issue token for")
    email: Optional[str] = Field(default=None, description="Optional user email")
    role: Optional[str] = Field(default="user", description="Optional user role")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    expires_in: int


@router.post("/token", response_model=TokenResponse)
def issue_token(payload: TokenRequest):
    """
    Issues a cryptographically signed JWT for development, testing, and client authentication.
    """
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
    return {
        "authenticated": True,
        "user_id": claims.get("sub"),
        "email": claims.get("email"),
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
