from datetime import date
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from backend.app import app
from backend.models.trip import TripRequest

client = TestClient(app)

FRONTEND_SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"

SAMPLE_TRIP_PAYLOAD = {
    "source": "Bengaluru, Karnataka, India",
    "destination": "Goa, India",
    "days": 3,
    "travel_mode": "car",
    "travelers": [
        {
            "name": "Jordan",
            "interests": ["Beaches"],
            "budget": "Medium",
            "pace": "Balanced",
        }
    ],
    "mandatory_visits": [],
}


# ============================================================================
# BACKEND SCHEMA & VALIDATION TESTS
# ============================================================================

def test_valid_same_month_date_selection():
    """Verify selecting start and end dates within the same month computes days correctly."""
    req = TripRequest(
        **SAMPLE_TRIP_PAYLOAD,
        start_date="2026-10-15",
        end_date="2026-10-18",
    )
    assert req.start_date == "2026-10-15"
    assert req.end_date == "2026-10-18"
    assert req.days == 4  # 15, 16, 17, 18 inclusive


def test_cross_month_december_to_january_navigation():
    """Verify dates spanning December into January calculate duration across years correctly."""
    req = TripRequest(
        **SAMPLE_TRIP_PAYLOAD,
        start_date="2026-12-30",
        end_date="2027-01-03",
    )
    assert req.start_date == "2026-12-30"
    assert req.end_date == "2027-01-03"
    # Dec 30, Dec 31, Jan 1, Jan 2, Jan 3 = 5 days
    assert req.days == 5


def test_leap_year_february_vs_ordinary_february():
    """Verify leap-year February (29 days) and non-leap February (28 days) duration calculations."""
    # 2028 is a leap year: Feb 28 to Mar 2 = Feb 28, Feb 29, Mar 1, Mar 2 = 4 days
    req_leap = TripRequest(
        **SAMPLE_TRIP_PAYLOAD,
        start_date="2028-02-28",
        end_date="2028-03-02",
    )
    assert req_leap.days == 4

    # 2027 is not a leap year: Feb 27 to Mar 2 = Feb 27, Feb 28, Mar 1, Mar 2 = 4 days
    req_non_leap = TripRequest(
        **SAMPLE_TRIP_PAYLOAD,
        start_date="2027-02-27",
        end_date="2027-03-02",
    )
    assert req_non_leap.days == 4

    # 2027 Feb 28 to Mar 1 = Feb 28, Mar 1 = 2 days
    req_non_leap_short = TripRequest(
        **SAMPLE_TRIP_PAYLOAD,
        start_date="2027-02-28",
        end_date="2027-03-01",
    )
    assert req_non_leap_short.days == 2


def test_months_with_varying_day_counts():
    """Verify month boundary day calculations for 30-day and 31-day months."""
    # April has 30 days: Apr 29 to May 2 = Apr 29, Apr 30, May 1, May 2 = 4 days
    req_30 = TripRequest(
        **SAMPLE_TRIP_PAYLOAD,
        start_date="2026-04-29",
        end_date="2026-05-02",
    )
    assert req_30.days == 4

    # July has 31 days: Jul 30 to Aug 2 = Jul 30, Jul 31, Aug 1, Aug 2 = 4 days
    req_31 = TripRequest(
        **SAMPLE_TRIP_PAYLOAD,
        start_date="2026-07-30",
        end_date="2026-08-02",
    )
    assert req_31.days == 4


def test_reject_end_date_earlier_than_start_date():
    """Verify that an end date earlier than start date is rejected with ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TripRequest(
            **SAMPLE_TRIP_PAYLOAD,
            start_date="2026-10-20",
            end_date="2026-10-15",
        )
    assert "end_date cannot precede start_date" in str(exc_info.value)


def test_reject_incomplete_or_missing_date_selection():
    """Verify that providing start_date without end_date, or vice versa, is rejected."""
    # start_date provided, end_date missing
    with pytest.raises(ValidationError) as exc1:
        TripRequest(
            **SAMPLE_TRIP_PAYLOAD,
            start_date="2026-10-15",
            end_date=None,
        )
    assert "Both start_date and end_date must be provided" in str(exc1.value)

    # end_date provided, start_date missing
    with pytest.raises(ValidationError) as exc2:
        TripRequest(
            **SAMPLE_TRIP_PAYLOAD,
            start_date=None,
            end_date="2026-10-20",
        )
    assert "Both start_date and end_date must be provided" in str(exc2.value)


def test_reject_invalid_date_format():
    """Verify non-ISO date formats are rejected."""
    with pytest.raises(ValidationError) as exc:
        TripRequest(
            **SAMPLE_TRIP_PAYLOAD,
            start_date="15-10-2026",
            end_date="20-10-2026",
        )
    assert "YYYY-MM-DD" in str(exc.value)


def test_reject_range_exceeding_max_duration():
    """Verify date ranges exceeding maximum duration (30 days) are rejected."""
    with pytest.raises(ValidationError) as exc:
        TripRequest(
            **SAMPLE_TRIP_PAYLOAD,
            start_date="2026-10-01",
            end_date="2026-11-05",  # 36 days
        )
    assert "between 1 and 30 days" in str(exc.value)


def test_existing_trip_creation_without_dates_remains_intact():
    """Verify legacy requests without dates continue to function and enforce duration limits."""
    payload = {**SAMPLE_TRIP_PAYLOAD, "days": 5}
    req = TripRequest(**payload)
    assert req.days == 5
    assert req.start_date is None
    assert req.end_date is None


def test_date_serialization_in_api_response(tmp_path, monkeypatch):
    """Verify the API planner endpoint correctly accepts and serializes travel dates in the response."""
    payload = {
        **SAMPLE_TRIP_PAYLOAD,
        "start_date": "2026-11-10",
        "end_date": "2026-11-13",
    }
    response = client.post("/planner/", json=payload)
    assert response.status_code == 200, f"Planner request failed: {response.text}"
    data = response.json()
    assert "trip" in data
    trip = data["trip"]
    assert trip.get("start_date") == "2026-11-10"
    assert trip.get("end_date") == "2026-11-13"
    assert trip.get("days") == 4


# ============================================================================
# FRONTEND DATE UTILITIES & COMPONENT INTEGRATION VERIFICATION
# ============================================================================

def test_frontend_date_utils_file_structure():
    """Verify frontend/src/utils/dateUtils.ts exists and implements essential calendar logic."""
    date_utils_file = FRONTEND_SRC / "utils" / "dateUtils.ts"
    assert date_utils_file.exists(), "dateUtils.ts must exist"
    content = date_utils_file.read_text(encoding="utf-8")

    assert "isLeapYear" in content
    assert "getDaysInMonth" in content
    assert "getFirstDayOfWeek" in content
    assert "formatDateString" in content
    assert "calculateDaysBetween" in content
    assert "isDateInRange" in content
    assert "MONTH_NAMES" in content
    assert "DAY_NAMES" in content


def test_frontend_travel_date_picker_component():
    """Verify frontend/src/components/TravelDatePicker.tsx exists and implements navigation."""
    date_picker_file = FRONTEND_SRC / "components" / "TravelDatePicker.tsx"
    assert date_picker_file.exists(), "TravelDatePicker.tsx must exist"
    content = date_picker_file.read_text(encoding="utf-8")

    assert "handlePrevMonth" in content
    assert "handleNextMonth" in content
    assert "handleMonthSelect" in content
    assert "handleYearSelect" in content
    assert "handleDateClick" in content
    assert "maxTripDurationDays" in content
    assert "MONTH_NAMES" in content


def test_trip_form_integrates_travel_date_picker():
    """Verify TripForm.tsx integrates TravelDatePicker and validates travel dates on submission."""
    trip_form_file = FRONTEND_SRC / "components" / "TripForm.tsx"
    content = trip_form_file.read_text(encoding="utf-8")

    assert "TravelDatePicker" in content
    assert "startDate" in content
    assert "endDate" in content
    assert "calculateDaysBetween" in content
    assert "start_date: startDate" in content
    assert "end_date: endDate" in content
    assert "setDateValidationError" in content


def test_trip_request_type_includes_travel_dates():
    """Verify frontend/src/types/trip.ts includes optional start_date and end_date."""
    trip_types_file = FRONTEND_SRC / "types" / "trip.ts"
    content = trip_types_file.read_text(encoding="utf-8")

    assert "start_date?:" in content
    assert "end_date?:" in content
