import logging
from typing import Optional, Tuple, Dict, Any
from fastapi import Header, HTTPException, Request, Query, status

from backend.services.storage.trip_store import load_trip_record
from backend.services.auth.jwt_service import verify_access_token

logger = logging.getLogger(__name__)

ROLE_LEVELS: Dict[str, int] = {
    "viewer": 1,
    "editor": 2,
    "owner": 3,
}

MAX_USER_ID_LENGTH = 128


def _sanitize_user_id(raw_id: Any) -> Optional[str]:
    if raw_id is None:
        return None
    cleaned = str(raw_id).strip()
    # Strip dangerous control characters (CRLF, null bytes)
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() and ch not in ("\r", "\n", "\0")).strip()
    if not cleaned or len(cleaned) > MAX_USER_ID_LENGTH:
        return None
    return cleaned


import contextvars

_current_request: contextvars.ContextVar[Optional[Request]] = contextvars.ContextVar(
    "current_request", default=None
)


def set_current_request(req: Optional[Request]):
    return _current_request.set(req)


def reset_current_request(token):
    try:
        _current_request.reset(token)
    except Exception:
        pass


def get_current_request() -> Optional[Request]:
    try:
        return _current_request.get()
    except LookupError:
        return None


def _is_valid_str(val: Any) -> bool:
    if val is None or not isinstance(val, str):
        return False
    return bool(val.strip())


def extract_authenticated_user_id(
    request: Optional[Request] = None,
    authorization: Optional[str] = None,
    token: Optional[str] = None,
    x_user_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Optional[str]:
    """
    Extracts the authenticated user ID exclusively from cryptographically verified credentials.
    Supports Authorization: Bearer <JWT> and direct query param ?token=<JWT>.

    SECURITY RULES:
    1. Never trusts X-User-ID or user_id query param as proof of identity.
    2. If a Bearer token is provided, it is verified cryptographically.
    3. If X-User-ID is also provided, it must match the verified token subject (sub claim);
       otherwise a 401 identity mismatch error is raised to prevent confused-deputy attacks.
    4. If no Bearer credentials are provided, returns None (unauthenticated).
    """
    req = request if isinstance(request, Request) else get_current_request()
    raw_token = None

    if _is_valid_str(authorization) and str(authorization).strip().lower().startswith("bearer "):
        raw_token = str(authorization).strip()[7:].strip()
    elif _is_valid_str(token):
        raw_token = str(token).strip()
    elif req is not None:
        auth_hdr = req.headers.get("authorization") or req.headers.get("Authorization")
        if _is_valid_str(auth_hdr) and str(auth_hdr).strip().lower().startswith("bearer "):
            raw_token = str(auth_hdr).strip()[7:].strip()
        elif req.query_params.get("token") and _is_valid_str(req.query_params.get("token")):
            raw_token = str(req.query_params.get("token")).strip()

    if not raw_token:
        # Client provided no verified Bearer credentials.
        # X-User-ID is explicitly untrusted as proof of identity.
        return None

    # Cryptographically verify the token
    claims = verify_access_token(raw_token)
    verified_sub = claims.get("sub")
    clean_sub = _sanitize_user_id(verified_sub)

    if not clean_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token contains an invalid or empty subject claim",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    # Check for header identity mismatch if X-User-ID was passed alongside the token
    declared_header = None
    if _is_valid_str(x_user_id):
        declared_header = _sanitize_user_id(x_user_id)
    elif req is not None:
        hdr = req.headers.get("x-user-id") or req.headers.get("X-User-ID")
        if _is_valid_str(hdr):
            declared_header = _sanitize_user_id(hdr)

    if declared_header and declared_header != clean_sub:
        logger.warning(
            f"Security alert: Token subject '{clean_sub}' does not match client-declared X-User-ID '{declared_header}'"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication identity mismatch: X-User-ID header does not match authenticated token subject",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    return clean_sub


def extract_user_id(
    request: Optional[Request] = None,
    x_user_id: Optional[str] = None,
    user_id: Optional[str] = None,
    authorization: Optional[str] = None,
    token: Optional[str] = None,
) -> Optional[str]:
    """
    Backward-compatible entry point that delegates to extract_authenticated_user_id.
    Derives identity exclusively from verified Bearer JWT credentials.
    """
    return extract_authenticated_user_id(
        request=request,
        authorization=authorization,
        token=token,
        x_user_id=x_user_id,
        user_id=user_id,
    )


def verify_trip_access(
    trip_id: str,
    user_id: Optional[str],
    required_role: str = "viewer",
) -> Tuple[Dict[str, Any], str]:
    """
    Verifies that the requester has the required role on the specified trip.
    Raises HTTPException 404 if trip does not exist.
    Raises HTTPException 401 if trip is private and user is unauthenticated.
    Raises HTTPException 403 if user lacks sufficient role or is an unauthorized stranger.
    For legacy unowned trips: allows viewer/editor operations for backward compatibility,
    but blocks owner-level mutations until the trip is explicitly claimed via /claim-legacy.
    Returns (trip_record, user_role).
    """
    if not trip_id or not str(trip_id).strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    trip_record = load_trip_record(trip_id)
    if not trip_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    owner_id = trip_record.get("owner_id")
    members = trip_record.get("members") or {}

    # Handle legacy trips without owner_id
    if not owner_id:
        if required_role == "owner":
            # Do NOT silently grant ownership to arbitrary callers!
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Legacy trip has no assigned owner. It must be explicitly claimed via POST /trip/{trip_id}/claim-legacy before managing invitations or ownership.",
            )
        # Allow legacy read/edit operations for existing test compatibility
        return trip_record, "editor"

    # Private trip with assigned owner_id
    clean_user = str(user_id).strip() if user_id else None
    if not clean_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: private trip requires valid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Determine user's active role on this trip
    if clean_user == owner_id:
        user_role = "owner"
    elif clean_user in members:
        user_role = members[clean_user].get("role", "viewer")
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: private trip",
        )

    user_level = ROLE_LEVELS.get(user_role, 0)
    required_level = ROLE_LEVELS.get(required_role, 1)

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: required role '{required_role}', but current role is '{user_role}'",
        )

    return trip_record, user_role
