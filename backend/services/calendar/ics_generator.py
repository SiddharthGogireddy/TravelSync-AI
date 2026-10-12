"""
TravelSync AI - iCalendar (.ics) Exporter (RFC 5545)
Generates compliant, richly detailed .ics calendar files for saved trips.
Supports single-day, multi-day, multi-destination itineraries, attractions,
dining, rest breaks, and hotel milestones.
"""

from datetime import datetime, date, timedelta, timezone
import re
from typing import Dict, List, Optional, Any, Tuple


def escape_ics_text(text: Optional[str]) -> str:
    """
    Escapes text characters according to RFC 5545 section 3.3.11.
    Backslash, semicolon, comma, and line breaks are escaped.
    """
    if not text:
        return ""
    # Normalize newlines
    cleaned = str(text).replace("\r\n", "\n").replace("\r", "\n")
    # Escape backslashes first
    cleaned = cleaned.replace("\\", "\\\\")
    # Escape semicolons and commas
    cleaned = cleaned.replace(";", "\\;").replace(",", "\\,")
    # Escape newlines as literal \n
    cleaned = cleaned.replace("\n", "\\n")
    return cleaned


def fold_line(line: str, max_bytes: int = 75) -> str:
    """
    Folds lines longer than max_bytes according to RFC 5545.
    Continuation lines are prepended with a single space.
    """
    encoded = line.encode("utf-8")
    if len(encoded) <= max_bytes:
        return line

    chunks: List[str] = []
    idx = 0
    first = True
    while idx < len(encoded):
        limit = max_bytes if first else (max_bytes - 1)
        chunk_len = min(limit, len(encoded) - idx)
        # Avoid splitting in the middle of a multi-byte UTF-8 sequence
        while chunk_len > 0:
            try:
                chunk = encoded[idx:idx + chunk_len].decode("utf-8")
                break
            except UnicodeDecodeError:
                chunk_len -= 1

        if chunk_len == 0:
            chunk = encoded[idx:idx + 1].decode("utf-8", errors="replace")
            chunk_len = 1

        chunks.append(chunk)
        idx += chunk_len
        first = False

    return "\r\n ".join(chunks)


def parse_time_str(time_str: str) -> Optional[Tuple[int, int]]:
    """
    Parses a time string like '09:00 AM', '9:15 am', or '14:30' into (hour, minute).
    Returns None if parsing fails.
    """
    if not time_str or not isinstance(time_str, str):
        return None

    cleaned = time_str.strip().upper()
    # Try 12-hour format with AM/PM (e.g. '09:00 AM' or '9:30PM')
    m_12 = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", cleaned)
    if m_12:
        hour = int(m_12.group(1))
        minute = int(m_12.group(2))
        period = m_12.group(3)
        if period == "AM":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12
        return (hour, minute)

    # Try 24-hour format (e.g. '14:30' or '09:00')
    m_24 = re.match(r"^(\d{1,2}):(\d{2})$", cleaned)
    if m_24:
        hour = int(m_24.group(1))
        minute = int(m_24.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)

    return None


def parse_time_range(range_str: str) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """
    Parses a time range string like '09:00 AM - 10:15 AM' into start and end (hour, minute).
    """
    if not range_str or not isinstance(range_str, str) or "-" not in range_str:
        return None, None

    parts = range_str.split("-")
    if len(parts) == 2:
        start_t = parse_time_str(parts[0])
        end_t = parse_time_str(parts[1])
        return start_t, end_t
    return None, None


def resolve_base_date(trip_dict: Dict[str, Any]) -> Tuple[date, bool]:
    """
    Resolves the trip start calendar date.
    Returns (start_date, is_specified). If is_specified is False, a reference fallback date is used.
    """
    start_date_str = trip_dict.get("start_date")
    if not start_date_str and isinstance(trip_dict.get("travel_dates"), dict):
        start_date_str = trip_dict["travel_dates"].get("start_date")

    if start_date_str and isinstance(start_date_str, str):
        try:
            return datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date(), True
        except ValueError:
            pass

    # Try 'dates' field (e.g., '2026-11-01 to 2026-11-05')
    dates_str = trip_dict.get("dates")
    if dates_str and isinstance(dates_str, str):
        match = re.search(r"(\d{4}-\d{2}-\d{2})", dates_str)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d").date(), True
            except ValueError:
                pass

    # Fallback to created_at or today's date
    created_at = trip_dict.get("created_at")
    if created_at and isinstance(created_at, str):
        match = re.search(r"(\d{4}-\d{2}-\d{2})", created_at)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d").date(), False
            except ValueError:
                pass

    return datetime.now(timezone.utc).date(), False


def get_calendar_filename(trip_dict: Dict[str, Any], trip_id: str) -> str:
    """
    Builds a clean, safe download filename for the .ics file.
    Example: TravelSync_Paris_2026-11-01.ics
    """
    dest = (trip_dict.get("destination") or "Trip").split(",")[0].strip()
    # If composite multi-destination
    if "->" in dest:
        dest = dest.replace("->", "to")
    safe_dest = re.sub(r'[<>:"/\\|?* ]', '_', dest).strip("_") or "Itinerary"

    start_date_str = trip_dict.get("start_date")
    if start_date_str and isinstance(start_date_str, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", start_date_str.strip()):
        date_part = start_date_str.strip()
    else:
        date_part = trip_id[:8] if trip_id else "export"

    return f"TravelSync_{safe_dest}_{date_part}.ics"


def generate_trip_ics(trip_wrapper: Dict[str, Any], trip_id: str) -> str:
    """
    Generates an RFC 5545 compliant iCalendar string for a trip.
    Handles single-day, multi-day, multi-destination, attractions, meals,
    rest breaks, and hotel check-in/out milestones.
    """
    trip_dict = trip_wrapper.get("trip", trip_wrapper) if isinstance(trip_wrapper, dict) else {}
    base_date, date_is_specified = resolve_base_date(trip_dict)

    now_utc = datetime.now(timezone.utc)
    dtstamp = now_utc.strftime("%Y%m%dT%H%M%SZ")

    dest_name = trip_dict.get("destination") or "Itinerary"
    src_name = trip_dict.get("source") or ""
    cal_name = f"TravelSync - {dest_name}"
    cal_desc = f"Trip itinerary for {dest_name} generated by TravelSync AI."
    if not date_is_specified:
        cal_desc += f" (Note: Travel start date was not specified; events are scheduled relative to reference date {base_date.isoformat()}.)"

    lines: List[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TravelSync AI//Trip Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        f"X-WR-CALDESC:{cal_desc}",
    ]

    day_schedule = trip_dict.get("day_schedule") or {}
    meals_and_breaks = trip_dict.get("meals_and_breaks") or {}
    hotels = trip_dict.get("hotels") or []
    days_count = trip_dict.get("days") or len(day_schedule) or 1

    # Sort day keys numerically
    sorted_days: List[int] = []
    for k in day_schedule.keys():
        try:
            sorted_days.append(int(k))
        except (ValueError, TypeError):
            pass
    if not sorted_days:
        try:
            sorted_days = list(range(1, int(days_count) + 1))
        except Exception:
            sorted_days = [1]
    sorted_days.sort()

    event_counter = 0

    # 1. Hotel Check-In Event (on Day 1)
    if hotels and len(hotels) > 0 and len(sorted_days) > 0:
        first_hotel = hotels[0]
        h_name = first_hotel.get("name", "Recommended Hotel")
        day_1_date = base_date
        checkin_start = datetime(day_1_date.year, day_1_date.month, day_1_date.day, 14, 0)
        checkin_end = datetime(day_1_date.year, day_1_date.month, day_1_date.day, 15, 0)
        event_counter += 1

        desc_lines = [
            f"Hotel Check-in: {h_name}",
            f"Destination: {dest_name}",
            "Standard check-in time: 02:00 PM (subject to property policy).",
        ]
        if first_hotel.get("distance_km"):
            desc_lines.append(f"Distance from destination center: {first_hotel['distance_km']} km")
        if not date_is_specified:
            desc_lines.append(f"Note: Scheduled for Day 1 relative to reference date {day_1_date.isoformat()}.")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:travelsync-{trip_id}-hotel-checkin@{trip_id[:8]}.local",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{checkin_start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{checkin_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{escape_ics_text(f'Hotel Check-in: {h_name}')}",
            f"DESCRIPTION:{escape_ics_text('\\n'.join(desc_lines))}",
            f"LOCATION:{escape_ics_text(h_name)}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    # 2. Iterate each day's schedule
    for day_num in sorted_days:
        day_str = str(day_num)
        day_date = base_date + timedelta(days=day_num - 1)
        day_places = day_schedule.get(day_str) or []

        # Inter-destination transit note if day 1 of a new destination leg
        destinations = trip_dict.get("destinations")
        current_dest_label = dest_name
        if destinations and isinstance(destinations, list) and len(destinations) >= day_num:
            stop_obj = destinations[day_num - 1]
            if isinstance(stop_obj, dict) and stop_obj.get("name"):
                current_dest_label = stop_obj["name"]

        # Attractions for this day
        for p_idx, place in enumerate(day_places):
            if not isinstance(place, dict):
                continue

            event_counter += 1
            p_name = place.get("name") or f"Attraction {p_idx + 1}"
            p_cat = place.get("category") or "Sightseeing"
            p_desc = place.get("description") or place.get("explanation") or ""
            lat = place.get("lat")
            lon = place.get("lon")

            # Determine timing
            start_t: Optional[Tuple[int, int]] = None
            end_t: Optional[Tuple[int, int]] = None

            if place.get("arrival_time") and place.get("departure_time"):
                start_t = parse_time_str(place["arrival_time"])
                end_t = parse_time_str(place["departure_time"])
            elif place.get("time_window"):
                start_t, end_t = parse_time_range(place["time_window"])
            elif place.get("arrival_time"):
                start_t = parse_time_str(place["arrival_time"])
                if start_t:
                    dur_mins = int(place.get("visit_duration_minutes") or 60)
                    end_minutes = start_t[0] * 60 + start_t[1] + dur_mins
                    end_t = ((end_minutes // 60) % 24, end_minutes % 60)

            # Build description
            desc_parts = [
                f"Attraction: {p_name}",
                f"Category: {p_cat}",
                f"Itinerary: Day {day_num} ({current_dest_label})",
            ]
            if p_desc:
                desc_parts.append(f"Overview: {p_desc}")
            if place.get("travel_time_minutes"):
                desc_parts.append(f"Transit Time: ~{place['travel_time_minutes']} mins from prior stop")
            if place.get("opening_hours"):
                oh = place["opening_hours"]
                if isinstance(oh, dict) and oh.get("display"):
                    desc_parts.append(f"Operating Hours: {oh['display']}")
            if lat is not None and lon is not None:
                desc_parts.append(f"Maps: https://www.google.com/maps/search/?api=1&query={lat},{lon}")
            if not date_is_specified:
                desc_parts.append(f"Note: Scheduled for Day {day_num} relative to reference date {day_date.isoformat()}.")

            # Stable UID
            clean_p_slug = re.sub(r'[^a-zA-Z0-9]', '', p_name)[:16].lower() or "place"
            event_uid = f"travelsync-{trip_id}-d{day_num}-act{p_idx}-{clean_p_slug}@{trip_id[:8]}.local"

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{event_uid}")
            lines.append(f"DTSTAMP:{dtstamp}")

            if start_t and end_t:
                # Timed event
                dt_start = datetime(day_date.year, day_date.month, day_date.day, start_t[0], start_t[1])
                # Check for midnight span
                if (end_t[0] * 60 + end_t[1]) < (start_t[0] * 60 + start_t[1]):
                    next_day = day_date + timedelta(days=1)
                    dt_end = datetime(next_day.year, next_day.month, next_day.day, end_t[0], end_t[1])
                else:
                    dt_end = datetime(day_date.year, day_date.month, day_date.day, end_t[0], end_t[1])

                lines.append(f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}")
                lines.append(f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}")
            else:
                # All-day fallback event without fake clock time
                desc_parts.append("Note: Visit time flexible (all-day event schedule).")
                next_day = day_date + timedelta(days=1)
                lines.append(f"DTSTART;VALUE=DATE:{day_date.strftime('%Y%m%d')}")
                lines.append(f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}")

            lines.append(f"SUMMARY:{escape_ics_text(f'{p_name} ({p_cat})')}")
            lines.append(f"DESCRIPTION:{escape_ics_text('\\n'.join(desc_parts))}")
            lines.append(f"LOCATION:{escape_ics_text(p_name)}")
            if lat is not None and lon is not None:
                lines.append(f"GEO:{lat};{lon}")
                lines.append(f"URL:https://www.google.com/maps/search/?api=1&query={lat},{lon}")
            lines.append("STATUS:CONFIRMED")
            lines.append("END:VEVENT")

        # Meals for this day
        day_meals_info = meals_and_breaks.get(day_str) or {}
        day_meals = day_meals_info.get("meals") or []
        for m_idx, meal in enumerate(day_meals):
            if not isinstance(meal, dict):
                continue

            event_counter += 1
            m_type = meal.get("meal_type") or f"Meal {m_idx + 1}"
            m_name = meal.get("name") or f"{m_type} Stop"
            m_cuisine = meal.get("cuisine") or ""
            m_cost = meal.get("estimated_cost_per_person")
            m_slot = meal.get("time_slot") or ""

            start_t, end_t = parse_time_range(m_slot)
            if not start_t:
                # Sensible default meal hours if time_slot missing
                if "breakfast" in m_type.lower():
                    start_t, end_t = (8, 30), (9, 30)
                elif "lunch" in m_type.lower():
                    start_t, end_t = (13, 0), (14, 0)
                else:
                    start_t, end_t = (20, 0), (21, 30)

            dt_start = datetime(day_date.year, day_date.month, day_date.day, start_t[0], start_t[1])
            if (end_t[0] * 60 + end_t[1]) < (start_t[0] * 60 + start_t[1]):
                next_day = day_date + timedelta(days=1)
                dt_end = datetime(next_day.year, next_day.month, next_day.day, end_t[0], end_t[1])
            else:
                dt_end = datetime(day_date.year, day_date.month, day_date.day, end_t[0], end_t[1])

            desc_parts = [
                f"{m_type}: {m_name}",
                f"Day {day_num} Dining Stop",
            ]
            if m_cuisine:
                desc_parts.append(f"Cuisine / Speciality: {m_cuisine}")
            if m_cost is not None:
                desc_parts.append(f"Estimated Cost: ~INR {m_cost} per person")
            if meal.get("near_location"):
                desc_parts.append(f"Location Context: Near {meal['near_location']}")
            if not date_is_specified:
                desc_parts.append(f"Note: Scheduled for Day {day_num} relative to reference date {day_date.isoformat()}.")

            m_uid = f"travelsync-{trip_id}-d{day_num}-meal-{m_type.lower()[:8]}@{trip_id[:8]}.local"

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{m_uid}")
            lines.append(f"DTSTAMP:{dtstamp}")
            lines.append(f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}")
            lines.append(f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}")
            lines.append(f"SUMMARY:{escape_ics_text(f'{m_type}: {m_name}')}")
            lines.append(f"DESCRIPTION:{escape_ics_text('\\n'.join(desc_parts))}")
            lines.append(f"LOCATION:{escape_ics_text(m_name)}")
            lines.append("STATUS:CONFIRMED")
            lines.append("END:VEVENT")

        # Rest breaks for this day
        day_breaks = day_meals_info.get("rest_breaks") or []
        for b_idx, r_break in enumerate(day_breaks):
            if not isinstance(r_break, dict):
                continue

            event_counter += 1
            b_type = r_break.get("break_type") or "Rest Break"
            b_slot = r_break.get("time_slot") or "04:00 PM - 04:30 PM"
            start_t, end_t = parse_time_range(b_slot)
            if not start_t:
                start_t, end_t = (16, 0), (16, 30)

            dt_start = datetime(day_date.year, day_date.month, day_date.day, start_t[0], start_t[1])
            dt_end = datetime(day_date.year, day_date.month, day_date.day, end_t[0], end_t[1])

            desc_parts = [
                f"Rest Break: {b_type}",
                f"Day {day_num} Itinerary Pause",
            ]
            if r_break.get("recommended_activity"):
                desc_parts.append(f"Recommended Activity: {r_break['recommended_activity']}")
            if r_break.get("reason"):
                desc_parts.append(f"Reason: {r_break['reason']}")
            if r_break.get("location_context"):
                desc_parts.append(f"Location: {r_break['location_context']}")

            b_uid = f"travelsync-{trip_id}-d{day_num}-break{b_idx}@{trip_id[:8]}.local"

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{b_uid}")
            lines.append(f"DTSTAMP:{dtstamp}")
            lines.append(f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}")
            lines.append(f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}")
            lines.append(f"SUMMARY:{escape_ics_text(f'Break: {b_type}')}")
            lines.append(f"DESCRIPTION:{escape_ics_text('\\n'.join(desc_parts))}")
            lines.append("STATUS:CONFIRMED")
            lines.append("END:VEVENT")

    # 3. Hotel Check-Out Event (on last day)
    if hotels and len(hotels) > 0 and len(sorted_days) > 0:
        first_hotel = hotels[0]
        h_name = first_hotel.get("name", "Recommended Hotel")
        last_day_num = sorted_days[-1]
        last_day_date = base_date + timedelta(days=last_day_num - 1)
        checkout_start = datetime(last_day_date.year, last_day_date.month, last_day_date.day, 11, 0)
        checkout_end = datetime(last_day_date.year, last_day_date.month, last_day_date.day, 12, 0)

        desc_lines = [
            f"Hotel Check-out: {h_name}",
            f"Destination: {dest_name}",
            "Standard check-out time: 11:00 AM (settle room charges and depart).",
        ]

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:travelsync-{trip_id}-hotel-checkout@{trip_id[:8]}.local",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{checkout_start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{checkout_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{escape_ics_text(f'Hotel Check-out: {h_name}')}",
            f"DESCRIPTION:{escape_ics_text('\\n'.join(desc_lines))}",
            f"LOCATION:{escape_ics_text(h_name)}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    # Fold all lines per RFC 5545 (<= 75 bytes) and join with CRLF
    folded_lines = [fold_line(line) for line in lines]
    return "\r\n".join(folded_lines) + "\r\n"
