"""
Unit and integration tests for Step 72: Export Itinerary to Calendar (.ics).
Validates RFC 5545 compliance, single-day, multi-day, month-spanning,
multi-destination, stable UIDs, special characters, all-day fallbacks,
non-mutation of saved data, and frontend integration.
"""

import os
import sys
import copy
from datetime import datetime, date, timedelta
from pathlib import Path
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from backend.app import app
from backend.services.storage.trip_store import save_trip, load_trip
from backend.services.calendar.ics_generator import (
    escape_ics_text,
    fold_line,
    parse_time_str,
    parse_time_range,
    generate_trip_ics,
    get_calendar_filename,
)

client = TestClient(app)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC = BASE_DIR / "frontend" / "src"


def _create_base_trip_payload(
    destination="Jaipur",
    source="Delhi",
    days=1,
    start_date="2026-10-15",
    end_date=None,
    places=None,
    day_schedule=None,
    hotels=None,
    is_multi=False,
):
    if end_date is None and start_date:
        st_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = (st_dt + timedelta(days=days - 1)).strftime("%Y-%m-%d")

    return {
        "trip": {
            "source": source,
            "destination": destination,
            "days": days,
            "start_date": start_date,
            "end_date": end_date,
            "is_multi_destination": is_multi,
            "travel_mode": "car",
            "travelers": [{"name": "Priya", "interests": ["Heritage"], "budget": "Medium", "pace": "Balanced"}],
            "destination_location": {"lat": 26.9124, "lon": 75.7873},
            "hotels": hotels or [
                {"name": "ITC Rajputana", "lat": 26.920, "lon": 75.790, "distance_km": 2.5}
            ],
            "places": places or [
                {"name": "Hawa Mahal", "category": "Palace", "lat": 26.9239, "lon": 75.8267},
                {"name": "Amber Fort", "category": "Fort", "lat": 26.9855, "lon": 75.8513},
            ],
            "day_schedule": day_schedule if day_schedule is not None else {
                "1": [
                    {
                        "name": "Hawa Mahal",
                        "category": "Palace",
                        "lat": 26.9239,
                        "lon": 75.8267,
                        "arrival_time": "09:30 AM",
                        "departure_time": "11:00 AM",
                        "time_window": "09:30 AM - 11:00 AM",
                        "description": "Iconic honeycomb palace of winds",
                    },
                    {
                        "name": "Amber Fort",
                        "category": "Fort",
                        "lat": 26.9855,
                        "lon": 75.8513,
                        "arrival_time": "11:45 AM",
                        "departure_time": "02:00 PM",
                        "time_window": "11:45 AM - 02:00 PM",
                        "description": "Majestic hilltop fortress overlooking Maota Lake",
                    },
                ]
            },
            "meals_and_breaks": {
                "1": {
                    "meals": [
                        {
                            "meal_type": "Lunch",
                            "name": "1135 AD Amber",
                            "cuisine": "Royal Rajasthani Thali",
                            "time_slot": "01:15 PM - 02:15 PM",
                            "estimated_cost_per_person": 1200,
                        }
                    ],
                    "rest_breaks": [
                        {
                            "break_type": "Chai & Refreshment Pause",
                            "time_slot": "04:30 PM - 05:00 PM",
                            "recommended_activity": "Enjoy masala chai and relax legs",
                        }
                    ],
                }
            },
            "budget": {"total_budget": 15000, "estimated_cost": 8500},
        }
    }


def test_single_day_trip_calendar_export():
    """Verify single-day trip exports valid RFC 5545 .ics with correct times and headers."""
    raw = _create_base_trip_payload(days=1, start_date="2026-10-15")
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    assert "text/calendar" in res.headers["content-type"]
    assert 'attachment; filename="TravelSync_Jaipur_2026-10-15.ics"' in res.headers["content-disposition"]

    ics = res.text
    # RFC 5545 standard envelope
    assert "BEGIN:VCALENDAR" in ics
    assert "VERSION:2.0" in ics
    assert "PRODID:-//TravelSync AI//Trip Planner//EN" in ics
    assert "END:VCALENDAR" in ics

    # Events present
    assert "SUMMARY:Hawa Mahal (Palace)" in ics
    assert "SUMMARY:Amber Fort (Fort)" in ics
    assert "SUMMARY:Lunch: 1135 AD Amber" in ics
    assert "SUMMARY:Break: Chai & Refreshment Pause" in ics
    assert "SUMMARY:Hotel Check-in: ITC Rajputana" in ics
    assert "SUMMARY:Hotel Check-out: ITC Rajputana" in ics

    # Check times for Hawa Mahal on 2026-10-15
    assert "DTSTART:20261015T093000" in ics
    assert "DTEND:20261015T110000" in ics

    # Check lunch time (1:15 PM = 13:15, 2:15 PM = 14:15)
    assert "DTSTART:20261015T131500" in ics
    assert "DTEND:20261015T141500" in ics


def test_multi_day_trip_calendar_export():
    """Verify multi-day trip maps days to sequential calendar dates."""
    schedule = {
        "1": [{"name": "City Palace", "category": "Palace", "arrival_time": "10:00 AM", "departure_time": "12:00 PM"}],
        "2": [{"name": "Jantar Mantar", "category": "Observatory", "arrival_time": "09:00 AM", "departure_time": "10:30 AM"}],
        "3": [{"name": "Nahargarh Fort", "category": "Fort", "arrival_time": "03:00 PM", "departure_time": "05:30 PM"}],
    }
    raw = _create_base_trip_payload(days=3, start_date="2026-10-20", day_schedule=schedule)
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    ics = res.text

    # Day 1: 2026-10-20
    assert "DTSTART:20261020T100000" in ics
    assert "DTEND:20261020T120000" in ics

    # Day 2: 2026-10-21
    assert "DTSTART:20261021T090000" in ics
    assert "DTEND:20261021T103000" in ics

    # Day 3: 2026-10-22
    assert "DTSTART:20261022T150000" in ics
    assert "DTEND:20261022T173000" in ics

    # Hotel check-in on Day 1 (10-20), check-out on Day 3 (10-22)
    assert "DTSTART:20261020T140000" in ics
    assert "DTSTART:20261022T110000" in ics


def test_trip_spanning_calendar_months():
    """Verify trips crossing month boundaries (e.g., Oct 31 -> Nov 01) calculate dates accurately."""
    schedule = {
        "1": [{"name": "Spooky Tour", "category": "Tour", "arrival_time": "08:00 PM", "departure_time": "10:00 PM"}],
        "2": [{"name": "Morning Gardens", "category": "Park", "arrival_time": "09:00 AM", "departure_time": "10:30 AM"}],
        "3": [{"name": "Autumn Market", "category": "Market", "arrival_time": "02:00 PM", "departure_time": "04:00 PM"}],
    }
    raw = _create_base_trip_payload(days=3, start_date="2026-10-31", day_schedule=schedule)
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    ics = res.text

    # Day 1 = Oct 31, 2026
    assert "DTSTART:20261031T200000" in ics
    # Day 2 = Nov 1, 2026
    assert "DTSTART:20261101T090000" in ics
    # Day 3 = Nov 2, 2026
    assert "DTSTART:20261102T140000" in ics


def test_multi_destination_trip_calendar_export():
    """Verify multi-destination trip reflects destinations and leg ordering."""
    destinations = [
        {"name": "Bengaluru", "days": 1},
        {"name": "Mysuru", "days": 1},
    ]
    schedule = {
        "1": [{"name": "Lalbagh Botanical Garden", "category": "Garden", "arrival_time": "09:00 AM", "departure_time": "11:00 AM"}],
        "2": [{"name": "Mysore Palace", "category": "Palace", "arrival_time": "10:00 AM", "departure_time": "12:30 PM"}],
    }
    raw = _create_base_trip_payload(
        destination="Bengaluru -> Mysuru",
        days=2,
        start_date="2026-12-05",
        day_schedule=schedule,
        is_multi=True,
    )
    raw["trip"]["destinations"] = destinations
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    ics = res.text
    unfolded = ics.replace("\r\n ", "")

    assert "TravelSync_Bengaluru_to_Mysuru_2026-12-05.ics" in res.headers["content-disposition"]
    assert "Lalbagh Botanical Garden" in unfolded
    assert "Mysore Palace" in unfolded
    assert "Day 1 (Bengaluru)" in unfolded
    assert "Day 2 (Mysuru)" in unfolded


def test_event_ordering_and_stable_uids():
    """Verify event UIDs are deterministic across multiple exports of the same trip."""
    raw = _create_base_trip_payload(days=1, start_date="2026-10-15")
    trip_id = save_trip(raw)

    res1 = client.get(f"/trip/{trip_id}/export/calendar.ics")
    res2 = client.get(f"/trip/{trip_id}/export/calendar.ics")

    assert res1.status_code == 200
    assert res2.status_code == 200

    ics1_lines = [l for l in res1.text.splitlines() if l.startswith("UID:")]
    ics2_lines = [l for l in res2.text.splitlines() if l.startswith("UID:")]

    assert len(ics1_lines) > 0
    assert ics1_lines == ics2_lines, "UIDs must be completely stable and deterministic"

    # Verify UID structure format
    assert any("travelsync-" in uid for uid in ics1_lines)
    assert any("-act0-" in uid for uid in ics1_lines)


def test_missing_dates_or_missing_activity_times():
    """Verify fallback when trip start date or activity times are omitted."""
    schedule = {
        "1": [
            {
                "name": "Flexible Roaming Place",
                "category": "Sightseeing",
                "arrival_time": None,
                "departure_time": None,
                "time_window": None,
                # No clock times!
            }
        ]
    }
    raw = _create_base_trip_payload(days=1, start_date="", day_schedule=schedule)
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    ics = res.text

    # All-day fallback for missing activity time
    assert "DTSTART;VALUE=DATE:" in ics
    assert "DTEND;VALUE=DATE:" in ics
    assert "SUMMARY:Flexible Roaming Place (Sightseeing)" in ics
    assert "Note: Visit time flexible (all-day event schedule)." in ics

    # Documents reference fallback date when start date was not specified
    unfolded = ics.replace("\r\n ", "")
    assert "Travel start date was not specified" in unfolded


def test_special_characters_commas_semicolons_and_unicode():
    """Verify RFC 5545 escaping for commas, semicolons, backslashes, line breaks, and Unicode."""
    schedule = {
        "1": [
            {
                "name": "Café L'Étoile; Spécialité \\ \"Bordeaux, France\"",
                "category": "Culinary & Sights",
                "description": "Multi-line description with;\nsemicolons, commas, and \\ backslashes.\nPlus emojis: ⛩️ 🕌 🏰",
                "arrival_time": "10:00 AM",
                "departure_time": "11:30 AM",
            }
        ]
    }
    raw = _create_base_trip_payload(days=1, start_date="2026-11-10", day_schedule=schedule)
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    ics = res.text
    unfolded = ics.replace("\r\n ", "")

    # Commas, semicolons, and backslashes escaped in SUMMARY & DESCRIPTION
    assert "Café L'Étoile\\; Spécialité \\\\ \"Bordeaux\\, France\"" in unfolded
    assert "\\nsemicolons\\, commas\\, and \\\\ backslashes." in unfolded
    assert "⛩️ 🕌 🏰" in unfolded


def test_midnight_spanning_event_handling():
    """Verify events starting late and ending past midnight advance DTEND by one calendar day."""
    schedule = {
        "1": [
            {
                "name": "Midnight Astronomy & Stargazing",
                "category": "Activity",
                "arrival_time": "11:30 PM",
                "departure_time": "01:30 AM",
            }
        ]
    }
    raw = _create_base_trip_payload(days=1, start_date="2026-10-15", day_schedule=schedule)
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    ics = res.text

    # Starts on 2026-10-15 at 23:30, ends on 2026-10-16 at 01:30
    assert "DTSTART:20261015T233000" in ics
    assert "DTEND:20261016T013000" in ics


def test_empty_itinerary_handled_gracefully():
    """Verify trips with empty schedules or places do not raise 500 error."""
    raw = {
        "trip": {
            "destination": "Goa",
            "source": "Mumbai",
            "days": 1,
            "start_date": "2026-10-15",
            "day_schedule": {},
            "places": [],
            "hotels": [],
        }
    }
    trip_id = save_trip(raw)

    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200
    ics = res.text
    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics


def test_invalid_trip_id_returns_404():
    """Verify non-existent trip returns 404."""
    res = client.get("/trip/non-existent-uuid-99999/export/calendar.ics")
    assert res.status_code == 404
    assert res.json()["detail"] == "Trip not found"


def test_export_does_not_mutate_saved_trip_data():
    """Verify exporting does not mutate or regenerate saved trip data."""
    raw = _create_base_trip_payload(days=2, start_date="2026-10-15")
    trip_id = save_trip(raw)

    before_trip = load_trip(trip_id)

    # Perform calendar export
    res = client.get(f"/trip/{trip_id}/export/calendar.ics")
    assert res.status_code == 200

    after_trip = load_trip(trip_id)
    assert before_trip == after_trip, "Saved trip data must remain completely unchanged"


def test_frontend_calendar_export_integration():
    """Verify frontend api.ts and TripView.tsx expose Export to Calendar UI."""
    api_file = FRONTEND_SRC / "services" / "api.ts"
    assert api_file.exists()
    api_content = api_file.read_text(encoding="utf-8")
    assert "exportTripCalendar" in api_content
    assert "/export/calendar.ics" in api_content

    trip_view_file = FRONTEND_SRC / "pages" / "TripView.tsx"
    assert trip_view_file.exists()
    tv_content = trip_view_file.read_text(encoding="utf-8")
    assert "exportTripCalendar" in tv_content
    assert "export-calendar-btn" in tv_content
    assert "Export to Calendar" in tv_content
    assert "aria-label=" in tv_content
