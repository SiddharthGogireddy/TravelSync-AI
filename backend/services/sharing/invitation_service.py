import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List

from backend.services.storage.trip_store import (
    load_trip_record,
    update_trip_sharing,
    _read_trips,
    _STORE_LOCK,
)

logger = logging.getLogger(__name__)

VALID_ROLES = {"viewer", "editor"}
DEFAULT_EXPIRATION_DAYS = 7


def hash_token(raw_token: str) -> str:
    """Computes SHA-256 hash of a raw invitation token. Never logs raw tokens."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def _is_expired(expires_at_iso: str) -> bool:
    try:
        exp_dt = datetime.fromisoformat(expires_at_iso)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp_dt
    except Exception:
        return True


def create_invitation(
    trip_id: str,
    owner_user_id: str,
    role: str = "viewer",
    expires_in_days: int = DEFAULT_EXPIRATION_DAYS,
) -> Dict[str, Any]:
    """
    Creates a new unguessable invitation token with SHA-256 hashing.
    Only the owner of the trip may create invitations.
    Returns the invitation dictionary containing the one-time raw token.
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid invitation role '{role}'. Allowed roles: {list(VALID_ROLES)}")

    trip = load_trip_record(trip_id)
    if not trip:
        raise ValueError("Trip not found")

    # If trip has an owner, verify owner_user_id
    current_owner = trip.get("owner_id")
    if current_owner and current_owner != str(owner_user_id).strip():
        raise PermissionError("Only the trip owner can create invitations")

    # Generate cryptographically secure unguessable token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=max(1, int(expires_in_days)))).isoformat()
    invitation_id = str(uuid.uuid4())

    invitation = {
        "invitation_id": invitation_id,
        "token_hash": token_hash,
        "role": role,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "status": "pending",
        "created_by": str(owner_user_id).strip(),
        "accepted_by": None,
        "accepted_at": None,
    }

    with _STORE_LOCK:
        latest_trip = load_trip_record(trip_id)
        if not latest_trip:
            raise ValueError("Trip not found")
        current_invitations = list(latest_trip.get("invitations") or [])
        current_invitations.append(invitation)
        update_trip_sharing(trip_id, invitations=current_invitations)

    logger.info(
        "Created invitation %s for trip %s with role %s",
        invitation_id,
        trip_id,
        role,
    )

    # Return one-time token to caller
    return {
        "invitation_id": invitation_id,
        "trip_id": trip_id,
        "token": raw_token,
        "role": role,
        "created_at": invitation["created_at"],
        "expires_at": expires_at,
        "status": "pending",
    }


def list_trip_invitations(trip_id: str, requester_user_id: str) -> List[Dict[str, Any]]:
    """
    Lists invitations for a trip without exposing raw tokens or token hashes.
    Only the trip owner may list invitations.
    """
    trip = load_trip_record(trip_id)
    if not trip:
        raise ValueError("Trip not found")

    current_owner = trip.get("owner_id")
    if current_owner and current_owner != str(requester_user_id).strip():
        raise PermissionError("Only the trip owner can view invitation history")

    invitations = trip.get("invitations") or []
    safe_list = []
    for inv in invitations:
        status = inv.get("status", "pending")
        if status == "pending" and _is_expired(inv.get("expires_at", "")):
            status = "expired"

        safe_list.append({
            "invitation_id": inv.get("invitation_id"),
            "role": inv.get("role"),
            "created_at": inv.get("created_at"),
            "expires_at": inv.get("expires_at"),
            "status": status,
            "accepted_by": inv.get("accepted_by"),
            "accepted_at": inv.get("accepted_at"),
        })

    return safe_list


def revoke_invitation(trip_id: str, owner_user_id: str, invitation_id: str) -> bool:
    """
    Revokes a pending invitation.
    Only the trip owner may revoke invitations.
    """
    trip = load_trip_record(trip_id)
    if not trip:
        raise ValueError("Trip not found")

    current_owner = trip.get("owner_id")
    if current_owner and current_owner != str(owner_user_id).strip():
        raise PermissionError("Only the trip owner can revoke invitations")

    with _STORE_LOCK:
        latest_trip = load_trip_record(trip_id)
        if not latest_trip:
            return False
        invitations = list(latest_trip.get("invitations") or [])
        found = False
        for inv in invitations:
            if inv.get("invitation_id") == invitation_id:
                inv["status"] = "revoked"
                found = True
                break

        if not found:
            return False

        update_trip_sharing(trip_id, invitations=invitations)

    logger.info("Revoked invitation %s for trip %s", invitation_id, trip_id)
    return True


def find_invitation_by_token(raw_token: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Finds trip record and invitation matching the raw token's SHA-256 hash.
    Returns (trip_record, invitation_dict) or (None, None).
    """
    if not raw_token or not raw_token.strip():
        return None, None

    token_hash = hash_token(raw_token)
    with _STORE_LOCK:
        all_trips = _read_trips()
        for t in all_trips:
            if not isinstance(t, dict):
                continue
            invitations = t.get("invitations") or []
            for inv in invitations:
                if inv.get("token_hash") == token_hash:
                    return t, inv
    return None, None


def get_invitation_preview(raw_token: str) -> Dict[str, Any]:
    """
    Returns public preview information for an invitation token.
    Does not expose sensitive trip details if expired or revoked.
    """
    trip, invitation = find_invitation_by_token(raw_token)
    if not trip or not invitation:
        raise ValueError("Invalid invitation link")

    status = invitation.get("status", "pending")
    expired = _is_expired(invitation.get("expires_at", ""))
    if status == "pending" and expired:
        status = "expired"

    if status in ("revoked", "expired"):
        return {
            "valid": False,
            "status": status,
            "role": invitation.get("role", "viewer"),
            "trip_id": None,
            "destination": f"Invitation {status.capitalize()}",
            "source": f"Invitation {status.capitalize()}",
            "days": 0,
            "expires_at": invitation.get("expires_at"),
        }

    trip_data = trip.get("data") or {}
    trip_obj = trip_data.get("trip", {}) if isinstance(trip_data.get("trip"), dict) else trip_data

    destination = trip_obj.get("destination", "Unknown Destination")
    source = trip_obj.get("source", "Unknown Source")
    days = trip_obj.get("days", 1)

    return {
        "valid": status == "pending",
        "status": status,
        "role": invitation.get("role", "viewer"),
        "trip_id": trip.get("id"),
        "destination": destination,
        "source": source,
        "days": days,
        "expires_at": invitation.get("expires_at"),
    }


def accept_invitation(raw_token: str, user_id: str) -> Dict[str, Any]:
    """
    Accepts an invitation, adding user_id to trip members with the invitation's role.
    Atomically re-verifies invitation status inside lock to prevent concurrent double-acceptance.
    """
    if not user_id or not str(user_id).strip():
        raise ValueError("User ID is required to accept an invitation")

    uid = str(user_id).strip()
    trip, invitation = find_invitation_by_token(raw_token)
    if not trip or not invitation:
        raise ValueError("Invalid invitation link")

    trip_id = trip.get("id")
    role = invitation.get("role", "viewer")
    now_iso = datetime.now(timezone.utc).isoformat()
    token_hash = hash_token(raw_token)

    with _STORE_LOCK:
        # Re-fetch latest trip state under lock to guarantee atomic status verification
        latest_trip = load_trip_record(trip_id)
        if not latest_trip:
            raise ValueError("Trip no longer exists")

        invitations = list(latest_trip.get("invitations") or [])
        matching_inv = None
        for inv in invitations:
            if inv.get("token_hash") == token_hash:
                matching_inv = inv
                break

        if not matching_inv:
            raise ValueError("Invalid invitation link")

        current_status = matching_inv.get("status", "pending")
        if current_status == "revoked":
            raise ValueError("This invitation has been revoked by the trip owner")
        if current_status == "accepted":
            raise ValueError("This invitation has already been accepted")
        if current_status == "declined":
            raise ValueError("This invitation was previously declined")
        if _is_expired(matching_inv.get("expires_at", "")):
            raise ValueError("This invitation has expired")

        members = dict(latest_trip.get("members") or {})
        members[uid] = {
            "role": role,
            "joined_at": now_iso,
        }

        matching_inv["status"] = "accepted"
        matching_inv["accepted_by"] = uid
        matching_inv["accepted_at"] = now_iso

        update_trip_sharing(trip_id, members=members, invitations=invitations)

    logger.info("User %s accepted invitation to trip %s with role %s", uid, trip_id, role)
    return {
        "status": "accepted",
        "trip_id": trip_id,
        "role": role,
    }


def decline_invitation(raw_token: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Declines an invitation.
    Atomically re-verifies invitation status inside lock.
    """
    trip, invitation = find_invitation_by_token(raw_token)
    if not trip or not invitation:
        raise ValueError("Invalid invitation link")

    trip_id = trip.get("id")
    token_hash = hash_token(raw_token)

    with _STORE_LOCK:
        latest_trip = load_trip_record(trip_id)
        if not latest_trip:
            raise ValueError("Trip no longer exists")

        invitations = list(latest_trip.get("invitations") or [])
        matching_inv = None
        for inv in invitations:
            if inv.get("token_hash") == token_hash:
                matching_inv = inv
                break

        if not matching_inv:
            raise ValueError("Invalid invitation link")

        current_status = matching_inv.get("status", "pending")
        if current_status != "pending":
            raise ValueError(f"Invitation cannot be declined because it is already {current_status}")
        if _is_expired(matching_inv.get("expires_at", "")):
            raise ValueError("This invitation has expired")

        matching_inv["status"] = "declined"
        update_trip_sharing(trip_id, invitations=invitations)

    return {
        "status": "declined",
        "trip_id": trip_id,
    }
