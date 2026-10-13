import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# ==============================================================================
# JWT & OIDC CONFIGURATION
# ==============================================================================
DEFAULT_DEV_SECRET = "travelsync-dev-secret-key-32bytes-secure-2026-hardening"
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", DEFAULT_DEV_SECRET)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", str(7 * 24 * 3600)))  # 7 days

OIDC_ISSUER = os.getenv("OIDC_ISSUER", "travelsync-ai")
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "travelsync-api")
OIDC_JWKS_URL = os.getenv("OIDC_JWKS_URL", None)
AUTH_DEV_MODE = os.getenv("AUTH_DEV_MODE", "true").lower() in ("true", "1", "yes")

ALLOWED_ALGORITHMS = [JWT_ALGORITHM]
if JWT_ALGORITHM != "HS256" and "HS256" not in ALLOWED_ALGORITHMS:
    ALLOWED_ALGORITHMS.append("HS256")


def create_access_token(
    user_id: str,
    email: Optional[str] = None,
    role: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a cryptographically signed JWT access token.
    Claims include sub (user_id), iat, exp, iss, and aud.
    """
    if not user_id or not str(user_id).strip():
        raise ValueError("user_id is required to issue access token")

    clean_user = str(user_id).strip()
    now_ts = int(time.time())
    if expires_delta:
        exp_ts = now_ts + int(expires_delta.total_seconds())
    else:
        exp_ts = now_ts + JWT_EXPIRATION_SECONDS

    payload: Dict[str, Any] = {
        "sub": clean_user,
        "iat": now_ts,
        "exp": exp_ts,
        "iss": OIDC_ISSUER,
        "aud": OIDC_AUDIENCE,
    }

    if email:
        payload["email"] = str(email).strip()
    if role:
        payload["role"] = str(role).strip()
    if extra_claims:
        for k, v in extra_claims.items():
            if k not in payload:
                payload[k] = v

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Cryptographically verifies a JWT access token.
    Enforces signature validity, expiration, permitted algorithms, and subject claim.
    Raises HTTPException(401) on any verification failure.
    """
    if not token or not str(token).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clean_token = str(token).strip()

    # If OIDC JWKS is configured and token has RS256 header, attempt OIDC verification
    if OIDC_JWKS_URL:
        try:
            unverified_header = jwt.get_unverified_header(clean_token)
            if unverified_header.get("alg") in ("RS256", "ES256"):
                return verify_oidc_token(clean_token)
        except Exception:
            pass  # Fallback to standard HMAC verification

    try:
        payload = jwt.decode(
            clean_token,
            JWT_SECRET_KEY,
            algorithms=ALLOWED_ALGORITHMS,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "exp"],
            },
            audience=OIDC_AUDIENCE if OIDC_AUDIENCE else None,
            issuer=OIDC_ISSUER if OIDC_ISSUER else None,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The token has expired\""},
        )
    except jwt.InvalidAlgorithmError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token uses an unsupported algorithm",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed authentication token",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    sub = payload.get("sub")
    if not sub or not str(sub).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token lacks a valid subject claim",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    return payload


def verify_oidc_token(token: str) -> Dict[str, Any]:
    """
    Verifies an external OpenID Connect (OIDC) token against OIDC_JWKS_URL if configured.
    """
    if not OIDC_JWKS_URL:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="OIDC JWKS verification is not configured on this server",
        )

    try:
        jwks_client = jwt.PyJWKClient(OIDC_JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=OIDC_AUDIENCE if OIDC_AUDIENCE else None,
            issuer=OIDC_ISSUER if OIDC_ISSUER else None,
            options={"verify_exp": True, "require": ["sub", "exp"]},
        )
        return payload
    except Exception as e:
        logger.warning(f"OIDC token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OIDC token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )


def get_auth_config() -> Dict[str, Any]:
    """
    Returns non-sensitive auth configuration details for clients and setup docs.
    """
    return {
        "auth_provider": "oidc" if OIDC_JWKS_URL else "jwt",
        "algorithm": JWT_ALGORITHM,
        "issuer": OIDC_ISSUER,
        "audience": OIDC_AUDIENCE,
        "dev_mode": AUTH_DEV_MODE,
        "oidc_jwks_configured": bool(OIDC_JWKS_URL),
    }
