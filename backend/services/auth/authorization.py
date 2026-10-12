from typing import Optional, Tuple, Dict, Any
from fastapi import Header, HTTPException, Request, Query

from backend.services.storage.trip_store import load_trip_record

ROLE_LEVELS: Dict[str, int] = {
    "viewer": 1,
    "editor": 2,
    "owner": 3,
}


def extract_user_id(
    request: Optional[Request] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id: Optional[str] = Query(None),
) -> Optional[str]:
    """
    Extracts user ID from request header or query parameter.
    """
    if x_user_id and str(x_user_id).strip():
        return str(x_user_id).strip()
    if user_id and str(user_id).strip():
        return str(user_id).strip()
    if request:
        header_val = request.headers.get("x-user-id") or request.headers.get("X-User-ID")
        if header_val and header_val.strip():
            return header_val.strip()
    return None


def verify_trip_access(
    trip_id: str,
    user_id: Optional[str],
    required_role: str = "viewer",
) -> Tuple[Dict[str, Any], str]:
    """
    Verifies that the requester has the required role on the specified trip.
    Raises HTTPException 404 if trip does not exist.
    Raises HTTPException 403 if trip is private and user is unauthorized or lacks sufficient role.
    Returns (trip_record, user_role).
    """
    if not trip_id or not str(trip_id).strip():
        raise HTTPException(status_code=404, detail="Trip not found")

    trip_record = load_trip_record(trip_id)
    if not trip_record:
        raise HTTPException(status_code=404, detail="Trip not found")

    owner_id = trip_record.get("owner_id")
    members = trip_record.get("members") or {}

    # If the trip is legacy / unowned, allow access as owner for backward compatibility
    if not owner_id:
        return trip_record, "owner"

    clean_user = str(user_id).strip() if user_id else None
    if not clean_user:
        raise HTTPException(
            status_code=403,
            detail="Access denied: private trip",
        )

    # Determine user's active role on this trip
    if clean_user == owner_id:
        user_role = "owner"
    elif clean_user in members:
        user_role = members[clean_user].get("role", "viewer")
    else:
        raise HTTPException(
            status_code=403,
            detail="Access denied: private trip",
        )

    user_level = ROLE_LEVELS.get(user_role, 0)
    required_level = ROLE_LEVELS.get(required_role, 1)

    if user_level < required_level:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: required role '{required_role}', but current role is '{user_role}'",
        )

    return trip_record, user_role
