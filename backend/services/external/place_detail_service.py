import logging
import os
import re
import urllib.parse
from typing import Optional, Dict, Any, List
import httpx
from dotenv import load_dotenv

from backend.services.planner.opening_hours_scheduler import resolve_place_opening_hours

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENTRIPMAP_API_KEY")
OTM_XID_URL = "https://api.opentripmap.com/0.1/en/places/xid"

# In-memory cache for place details to avoid redundant external calls
_PLACE_DETAILS_CACHE: Dict[str, Dict[str, Any]] = {}


def _is_valid_http_url(url: Optional[str]) -> bool:
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    return url.startswith("http://") or url.startswith("https://")


async def fetch_wikipedia_details(name: str) -> Dict[str, Any]:
    """
    Fetches real encyclopedic details and verified representative photos
    from the public Wikimedia / Wikipedia Summary API.
    """
    if not name or not name.strip():
        return {}

    clean_name = re.sub(r"\(.*?\)", "", name).strip()
    encoded_title = urllib.parse.quote(clean_name.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"

    headers = {
        "User-Agent": "TravelSyncAI/1.0 (https://travelsync.ai; contact@travelsync.ai)"
    }

    try:
        async with httpx.AsyncClient(timeout=4.5) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if not isinstance(data, dict):
                    return {}

                thumbnail = data.get("thumbnail") or {}
                orig_image = data.get("originalimage") or {}
                image_url = orig_image.get("source") or thumbnail.get("source")

                content_urls = data.get("content_urls", {}).get("desktop", {})
                page_url = content_urls.get("page")

                coordinates = data.get("coordinates") or {}

                return {
                    "description": data.get("extract"),
                    "image_url": image_url if _is_valid_http_url(image_url) else None,
                    "image_source": "Wikimedia Commons" if image_url else None,
                    "website_url": page_url if _is_valid_http_url(page_url) else None,
                    "lat": coordinates.get("lat"),
                    "lon": coordinates.get("lon"),
                }
    except Exception as e:
        logger.debug(f"Wikipedia details lookup skipped or failed for '{name}': {e}")

    return {}


async def fetch_opentripmap_details(name: str, lat: Optional[float], lon: Optional[float]) -> Dict[str, Any]:
    """
    Attempts to fetch OpenTripMap xid details if coordinates are available.
    """
    if not API_KEY or lat is None or lon is None:
        return {}

    try:
        from backend.services.external.place_service import find_place
        place_meta = await find_place(name, lat, lon)
        if not place_meta or not isinstance(place_meta, dict):
            return {}

        xid = place_meta.get("xid")
        if not xid:
            return {}

        detail_url = f"{OTM_XID_URL}/{xid}"
        async with httpx.AsyncClient(timeout=4.5) as client:
            resp = await client.get(detail_url, params={"apikey": API_KEY})
            if resp.status_code == 200:
                data = resp.json()
                if not isinstance(data, dict):
                    return {}

                preview = data.get("preview") or {}
                image_url = data.get("image") or preview.get("source")

                address_dict = data.get("address") or {}
                address_parts = [
                    address_dict.get("road"),
                    address_dict.get("suburb"),
                    address_dict.get("city") or address_dict.get("town"),
                    address_dict.get("state"),
                    address_dict.get("country"),
                ]
                formatted_address = ", ".join([p for p in address_parts if p])

                rate = data.get("rate")
                provider_rating = float(rate) if rate is not None else None

                otm_url = data.get("url") or data.get("otm")

                wiki_extract = data.get("wikipedia_extracts", {}).get("text")

                return {
                    "image_url": image_url if _is_valid_http_url(image_url) else None,
                    "image_source": "OpenTripMap" if image_url else None,
                    "description": wiki_extract,
                    "address": formatted_address or None,
                    "provider_rating": provider_rating,
                    "provider_rating_source": "OpenTripMap Rate" if provider_rating is not None else None,
                    "website_url": otm_url if _is_valid_http_url(otm_url) else None,
                }
    except Exception as e:
        logger.debug(f"OpenTripMap details lookup skipped or failed for '{name}': {e}")

    return {}


async def get_place_details(
    name: str,
    place_type: str = "attraction",
    category: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    existing_place_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Aggregates rich, verified place details with graceful fallbacks.
    Never fabricates ratings, photos, review counts, or hotel availability.
    """
    clean_name = (name or "").strip()
    lat_key = round(lat, 2) if lat is not None else ""
    lon_key = round(lon, 2) if lon is not None else ""
    cache_key = f"{place_type.lower()}:{clean_name.lower()}:{lat_key}:{lon_key}"

    if cache_key in _PLACE_DETAILS_CACHE:
        return dict(_PLACE_DETAILS_CACHE[cache_key])

    existing = existing_place_data or {}
    effective_category = category or existing.get("category") or ("Hotel" if place_type == "hotel" else "Attraction")
    effective_lat = lat if lat is not None else existing.get("lat")
    effective_lon = lon if lon is not None else existing.get("lon")

    # Base record
    details: Dict[str, Any] = {
        "name": clean_name,
        "place_type": place_type.lower(),
        "category": effective_category,
        "description": existing.get("description") or existing.get("explanation"),
        "image_url": existing.get("image_url") if _is_valid_http_url(existing.get("image_url")) else None,
        "image_source": existing.get("image_source"),
        "address": existing.get("address"),
        "lat": effective_lat,
        "lon": effective_lon,
        "map_url": f"https://www.google.com/maps/search/?api=1&query={effective_lat},{effective_lon}" if effective_lat is not None and effective_lon is not None else None,
        "provider_rating": None,
        "provider_rating_source": None,
        "provider_reviews_count": None,
        "travelsync_match_score": existing.get("score"),
    }

    # Fetch Wikipedia summary
    wiki_info = None
    try:
        wiki_info = await fetch_wikipedia_details(clean_name)
    except Exception as e:
        logger.warning(f"Failed to fetch wikipedia details for {clean_name}: {e}")

    if wiki_info:
        if not details["image_url"] and _is_valid_http_url(wiki_info.get("image_url")):
            details["image_url"] = wiki_info["image_url"]
            details["image_source"] = wiki_info.get("image_source", "Wikipedia")
        if not details["description"] and wiki_info.get("description"):
            details["description"] = wiki_info["description"]
        if not details.get("website_url") and _is_valid_http_url(wiki_info.get("website_url")):
            details["website_url"] = wiki_info["website_url"]
        if details["lat"] is None and wiki_info.get("lat") is not None:
            details["lat"] = wiki_info["lat"]
            details["lon"] = wiki_info["lon"]
            details["map_url"] = f"https://www.google.com/maps/search/?api=1&query={wiki_info['lat']},{wiki_info['lon']}"

    # Fetch OpenTripMap detail if missing photo or address
    if effective_lat is not None and effective_lon is not None:
        otm_info = None
        try:
            otm_info = await fetch_opentripmap_details(clean_name, effective_lat, effective_lon)
        except Exception as e:
            logger.warning(f"Failed to fetch opentripmap details for {clean_name}: {e}")

        if otm_info:
            if not details["image_url"] and _is_valid_http_url(otm_info.get("image_url")):
                details["image_url"] = otm_info["image_url"]
                details["image_source"] = otm_info.get("image_source", "OpenTripMap")
            if not details["description"] and otm_info.get("description"):
                details["description"] = otm_info["description"]
            if not details["address"] and otm_info.get("address"):
                details["address"] = otm_info["address"]
            if details["provider_rating"] is None and otm_info.get("provider_rating") is not None:
                details["provider_rating"] = otm_info["provider_rating"]
                details["provider_rating_source"] = otm_info.get("provider_rating_source", "OpenTripMap")
            if not details.get("website_url") and _is_valid_http_url(otm_info.get("website_url")):
                details["website_url"] = otm_info["website_url"]

    # Provide helpful fallback description if none retrieved
    if not details["description"]:
        if place_type == "hotel":
            details["description"] = f"Selected accommodation option near the itinerary destination."
        else:
            cat_desc = effective_category.lower()
            details["description"] = f"Recommended {cat_desc} included in your itinerary stops."

    # Attraction practical visitor info
    if place_type != "hotel":
        opening_hours = existing.get("opening_hours")
        if not opening_hours:
            resolved_oh = resolve_place_opening_hours({"name": clean_name, "category": effective_category})
            opening_hours = {
                "opens": resolved_oh.get("opens", "09:00 AM"),
                "closes": resolved_oh.get("closes", "06:00 PM"),
                "display": resolved_oh.get("display", "09:00 AM - 06:00 PM"),
                "visit_duration_minutes": resolved_oh.get("visit_duration_minutes", 75),
                "closed_days": resolved_oh.get("closed_days", []),
            }
        details["opening_hours"] = opening_hours
        dur_mins = opening_hours.get("visit_duration_minutes", 60)
        details["estimated_visit_duration"] = f"~{dur_mins} mins"

        cat_lower = effective_category.lower()
        if any(k in cat_lower for k in ["park", "garden", "beach", "lake", "viewpoint"]):
            details["entry_fee"] = "Free / Public access"
            details["best_time_to_visit"] = "Morning or late afternoon"
        elif any(k in cat_lower for k in ["museum", "gallery"]):
            details["entry_fee"] = "Standard entry ticket required"
            details["best_time_to_visit"] = "Mid-day / Afternoon"
        elif any(k in cat_lower for k in ["fort", "palace", "monument", "heritage"]):
            details["entry_fee"] = "Visitor ticket required at entrance"
            details["best_time_to_visit"] = "Morning (cooler temperatures)"
        else:
            details["entry_fee"] = "Check entrance on arrival"
            details["best_time_to_visit"] = "Flexible visiting hours"

    # Hotel-specific fields
    if place_type == "hotel":
        details["star_rating"] = "Hospitality Accommodation"
        details["price_per_night"] = "Price varies by season & room type (Estimate)"
        details["amenities"] = ["Wi-Fi", "Front Desk", "Daily Housekeeping", "Parking (subject to availability)"]
        details["check_in_time"] = "02:00 PM (Standard)"
        details["check_out_time"] = "11:00 AM (Standard)"
        details["note"] = "Live availability and nightly rates require direct confirmation with the property."

    _PLACE_DETAILS_CACHE[cache_key] = details
    return details
