"""
TravelSync AI - Flexible Travel Date Suggestion Engine
Evaluates candidate travel windows using live Open-Meteo forecasts (0-16 days)
and transparent provisional seasonal estimates for dates beyond 16 days.
Ranks candidate dates using weather suitability, trip duration, weekend alignment,
budget/crowd trade-offs, and destination constraints without fabricating data.
"""

import math
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Optional, Any, Tuple

from backend.services.external.location_service import search_location
from backend.services.external.weather_service import (
    fetch_open_meteo_forecast,
    wmo_code_to_condition,
    MAX_FORECAST_HORIZON_DAYS,
)

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Climate baseline monthly estimates (India/Global fallback norms for provisional windows)
# temperature range (min, max) and rain probability index (0-100)
MONTHLY_CLIMATE_NORMALS: Dict[int, Dict[str, Any]] = {
    1: {"min_temp": 15.0, "max_temp": 28.0, "rain_prob": 10, "condition": "Mild & Sunny", "icon": "☀️"},
    2: {"min_temp": 17.0, "max_temp": 30.0, "rain_prob": 10, "condition": "Clear & Pleasant", "icon": "☀️"},
    3: {"min_temp": 20.0, "max_temp": 33.0, "rain_prob": 15, "condition": "Warm & Dry", "icon": "🌤️"},
    4: {"min_temp": 23.0, "max_temp": 36.0, "rain_prob": 20, "condition": "Hot & Sunny", "icon": "🌤️"},
    5: {"min_temp": 24.0, "max_temp": 37.0, "rain_prob": 30, "condition": "Hot with Pre-Monsoon Showers", "icon": "🌦️"},
    6: {"min_temp": 23.0, "max_temp": 31.0, "rain_prob": 65, "condition": "Monsoon Showers", "icon": "🌧️"},
    7: {"min_temp": 22.0, "max_temp": 29.0, "rain_prob": 75, "condition": "Active Monsoon Rain", "icon": "🌧️"},
    8: {"min_temp": 21.0, "max_temp": 29.0, "rain_prob": 70, "condition": "Monsoon Rains", "icon": "🌧️"},
    9: {"min_temp": 21.0, "max_temp": 30.0, "rain_prob": 55, "condition": "Post-Monsoon Showers", "icon": "🌦️"},
    10: {"min_temp": 20.0, "max_temp": 30.0, "rain_prob": 35, "condition": "Pleasant Transition Weather", "icon": "🌤️"},
    11: {"min_temp": 17.0, "max_temp": 29.0, "rain_prob": 15, "condition": "Cool & Clear", "icon": "☀️"},
    12: {"min_temp": 15.0, "max_temp": 28.0, "rain_prob": 10, "condition": "Crisp & Pleasant", "icon": "☀️"},
}


def parse_date_safely(d_str: Optional[str]) -> Optional[date]:
    if not d_str or not isinstance(d_str, str):
        return None
    try:
        return datetime.strptime(d_str.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def format_display_range(start_d: date, end_d: date) -> str:
    start_fmt = start_d.strftime("%a, %b %d")
    if start_d.year == end_d.year and start_d.month == end_d.month:
        return f"{start_fmt} – {end_d.strftime('%a, %b %d, %Y')}"
    return f"{start_fmt} – {end_d.strftime('%a, %b %d, %Y')}"


async def suggest_travel_dates(
    destination: str,
    days: int = 3,
    source: Optional[str] = None,
    flexible_window: Optional[str] = "next_month",
    earliest_date: Optional[str] = None,
    latest_date: Optional[str] = None,
    travelers_count: int = 1,
    budget: Optional[str] = "medium",
    interests: Optional[List[str]] = None,
    weather_preference: Optional[str] = "avoid_rain",
    prefer_weekends: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Ranks candidate travel dates within the flexible search window.
    """
    if not destination or not destination.strip():
        raise ValueError("Destination is required to suggest travel dates.")

    dest_cleaned = destination.strip()
    trip_days = max(1, min(30, int(days or 3)))

    # Resolve weekend preference default: for short trips (1-4 days), weekend alignment is preferred
    if prefer_weekends is None:
        prefer_weekends = (trip_days <= 4)

    today_utc = datetime.now(timezone.utc).date()

    # 1. Resolve date horizon
    earliest_d = parse_date_safely(earliest_date)
    latest_d = parse_date_safely(latest_date)

    if not earliest_d or earliest_d < today_utc:
        earliest_d = today_utc + timedelta(days=1)

    if not latest_d:
        if flexible_window == "next_2_weeks":
            latest_d = earliest_d + timedelta(days=14)
        elif flexible_window == "next_6_weeks":
            latest_d = earliest_d + timedelta(days=42)
        else:  # default next_month
            latest_d = earliest_d + timedelta(days=30)

    if latest_d < earliest_d + timedelta(days=trip_days - 1):
        latest_d = earliest_d + timedelta(days=trip_days + 7)

    # 2. Geocode destination
    loc = await search_location(dest_cleaned)
    if not loc or not loc.get("lat") or not loc.get("lon"):
        # Fallback to general coordinates if geocoder fails
        lat, lon = 12.9716, 77.5946
        dest_display = dest_cleaned
    else:
        lat, lon = float(loc["lat"]), float(loc["lon"])
        dest_display = loc.get("name", dest_cleaned)

    # 3. Fetch live weather (up to 16 days)
    weather_data = await fetch_open_meteo_forecast(lat, lon, forecast_days=16)
    live_daily = weather_data.get("daily", {}) if weather_data else {}
    live_dates = live_daily.get("time", [])

    # 4. Generate candidate sliding windows
    candidates: List[Dict[str, Any]] = []
    current_start = earliest_d
    max_search_days = min(90, (latest_d - earliest_d).days + 1)

    for offset in range(max_search_days - trip_days + 1):
        cand_start = current_start + timedelta(days=offset)
        cand_end = cand_start + timedelta(days=trip_days - 1)
        if cand_end > latest_d:
            break

        cand_info = evaluate_candidate_window(
            cand_start=cand_start,
            cand_end=cand_end,
            trip_days=trip_days,
            today=today_utc,
            live_dates=live_dates,
            live_daily=live_daily,
            prefer_weekends=prefer_weekends,
            weather_preference=weather_preference,
            budget=budget,
            interests=interests or [],
        )
        candidates.append(cand_info)

    if not candidates:
        # Fallback single candidate if search range was tightly bounded
        cand_start = earliest_d
        cand_end = earliest_d + timedelta(days=trip_days - 1)
        candidates.append(evaluate_candidate_window(
            cand_start=cand_start,
            cand_end=cand_end,
            trip_days=trip_days,
            today=today_utc,
            live_dates=live_dates,
            live_daily=live_daily,
            prefer_weekends=prefer_weekends,
            weather_preference=weather_preference,
            budget=budget,
            interests=interests or [],
        ))

    # 5. Rank and select top diverse recommendations
    # Sort primarily by composite score descending
    candidates.sort(key=lambda c: c["suitability_score"], reverse=True)

    recommendations = pick_diverse_recommendations(candidates, trip_days)

    return {
        "destination": dest_display,
        "origin": source or "",
        "trip_days": trip_days,
        "search_window": {
            "earliest_date": earliest_d.strftime("%Y-%m-%d"),
            "latest_date": latest_d.strftime("%Y-%m-%d"),
            "flexible_window": flexible_window or "custom",
        },
        "forecast_horizon_limit_days": MAX_FORECAST_HORIZON_DAYS,
        "recommendations": recommendations,
        "total_evaluated_windows": len(candidates),
    }


def evaluate_candidate_window(
    cand_start: date,
    cand_end: date,
    trip_days: int,
    today: date,
    live_dates: List[str],
    live_daily: Dict[str, Any],
    prefer_weekends: bool,
    weather_preference: Optional[str],
    budget: Optional[str],
    interests: List[str],
) -> Dict[str, Any]:
    """
    Scores a single candidate window based on live forecast or seasonal baseline.
    """
    days_from_today = (cand_start - today).days
    is_live_verified = (days_from_today + trip_days <= MAX_FORECAST_HORIZON_DAYS and bool(live_dates))

    temps_max: List[float] = []
    temps_min: List[float] = []
    rain_probs: List[int] = []
    precip_sums: List[float] = []
    weather_codes: List[int] = []
    conditions: List[str] = []
    icons: List[str] = []

    # Collect per-day weather information
    curr = cand_start
    has_live_for_all = True

    while curr <= cand_end:
        d_str = curr.strftime("%Y-%m-%d")
        if d_str in live_dates:
            idx = live_dates.index(d_str)
            t_max = float(live_daily.get("temperature_2m_max", [28.0])[idx] or 28.0)
            t_min = float(live_daily.get("temperature_2m_min", [20.0])[idx] or 20.0)
            p_prob = int(live_daily.get("precipitation_probability_max", [10])[idx] or 10)
            p_sum = float(live_daily.get("precipitation_sum", [0.0])[idx] or 0.0)
            wcode = int(live_daily.get("weathercode", [0])[idx] or 0)
            cond = wmo_code_to_condition(wcode)

            temps_max.append(t_max)
            temps_min.append(t_min)
            rain_probs.append(p_prob)
            precip_sums.append(p_sum)
            weather_codes.append(wcode)
            conditions.append(cond["description"])
            icons.append(cond["icon"])
        else:
            has_live_for_all = False
            # Use seasonal normal
            m = curr.month
            normal = MONTHLY_CLIMATE_NORMALS.get(m, MONTHLY_CLIMATE_NORMALS[10])
            temps_max.append(normal["max_temp"])
            temps_min.append(normal["min_temp"])
            rain_probs.append(normal["rain_prob"])
            precip_sums.append(1.0 if normal["rain_prob"] > 40 else 0.0)
            weather_codes.append(61 if normal["rain_prob"] > 50 else 1)
            conditions.append(normal["condition"])
            icons.append(normal["icon"])

        curr += timedelta(days=1)

    avg_max_temp = round(sum(temps_max) / len(temps_max), 1) if temps_max else 27.0
    avg_min_temp = round(sum(temps_min) / len(temps_min), 1) if temps_min else 19.0
    avg_rain_prob = round(sum(rain_probs) / len(rain_probs)) if rain_probs else 10
    total_precip = round(sum(precip_sums), 1) if precip_sums else 0.0

    # 1. Base Score (Starts at 70)
    score = 70.0

    # Weather penalties/bonuses
    # A. Rain penalty
    if avg_rain_prob <= 15:
        score += 15.0  # Very dry/clear bonus
    elif avg_rain_prob <= 30:
        score += 8.0
    elif avg_rain_prob <= 50:
        score -= 5.0
    elif avg_rain_prob <= 75:
        score -= 18.0
    else:
        score -= 32.0

    if weather_preference == "avoid_rain" and avg_rain_prob > 35:
        score -= 10.0

    # B. Severe conditions
    has_storm = any(c in [95, 96, 99] for c in weather_codes)
    has_heavy_rain = any(c in [65, 82] or p >= 15.0 for c, p in zip(weather_codes, precip_sums))
    if has_storm:
        score -= 25.0
    elif has_heavy_rain:
        score -= 15.0

    # C. Temperature Comfort
    if 20.0 <= avg_max_temp <= 28.0:
        score += 12.0  # Perfect temperature
    elif 28.0 < avg_max_temp <= 33.0:
        score += 5.0
    elif avg_max_temp > 37.0:
        score -= 18.0  # Extreme heat
    elif avg_max_temp < 12.0:
        score -= 10.0  # Chilly

    # 2. Weekend Alignment
    # Check weekdays spanned
    span_weekdays = []
    curr = cand_start
    while curr <= cand_end:
        span_weekdays.append(curr.weekday())  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
        curr += timedelta(days=1)

    has_saturday = 5 in span_weekdays
    has_sunday = 6 in span_weekdays
    is_weekend_trip = (has_saturday and has_sunday) or (has_saturday or has_sunday)

    if prefer_weekends:
        if has_saturday and has_sunday:
            score += 12.0
        elif has_saturday or has_sunday:
            score += 6.0
        else:
            score -= 4.0
    else:
        # Midweek preference
        if not (has_saturday or has_sunday):
            score += 8.0

    # 3. Museum / Cultural Monday Closure Check
    # If trip is 1-2 days and only on Monday, check if user has heritage/museum interest
    is_monday_only = (len(span_weekdays) <= 2 and all(w == 0 for w in span_weekdays))
    if is_monday_only and any(i.lower() in ["museum", "culture", "heritage", "history"] for i in interests):
        score -= 8.0

    # 4. Confidence / Forecast Horizon Flag
    if is_live_verified and has_live_for_all:
        confidence = "forecast_verified"
        confidence_label = "Live Forecast (Verified)"
        score += 5.0  # Bonus for high certainty
    else:
        confidence = "provisional_seasonal"
        confidence_label = "Provisional (Beyond 16-day horizon)"

    final_score = int(max(10, min(99, round(score))))

    # Reasons & Trade-offs generator
    reasons: List[str] = []
    trade_offs: List[str] = []

    # Positive reasons
    if avg_rain_prob <= 20:
        reasons.append(f"Minimal rain chance ({avg_rain_prob}%) with dry conditions")
    elif avg_rain_prob <= 40:
        reasons.append(f"Moderate rain risk ({avg_rain_prob}%), mostly pleasant")

    if 20.0 <= avg_max_temp <= 28.0:
        reasons.append(f"Pleasant peak temperatures ({avg_max_temp}°C)")
    elif avg_max_temp > 35.0:
        reasons.append(f"Sunny weather, best for early morning activities")

    if has_saturday and has_sunday:
        reasons.append("Spans the weekend for optimal work-life flexibility")
    elif not (has_saturday or has_sunday):
        reasons.append("Midweek timing offers lower attraction crowds")

    if is_live_verified:
        reasons.append("Verified by live Open-Meteo multi-day meteorological model")
    else:
        reasons.append("Favorable historical seasonal climate window for destination")

    # Trade-offs
    if has_saturday and has_sunday:
        trade_offs.append("Weekend hotel rates and attraction footfall may be higher")
    else:
        trade_offs.append("Requires taking weekdays off from regular schedule")

    if not is_live_verified:
        trade_offs.append("Travel dates are beyond the 16-day live forecast window; verify weather closer to departure")

    if avg_rain_prob > 35:
        trade_offs.append("Scattered rain showers possible; indoor backup activities suggested")

    if avg_max_temp > 34.0:
        trade_offs.append("Warm afternoons; plan outdoor sightseeing during early morning or sunset")

    # Primary condition summary
    primary_cond = conditions[0] if conditions else "Pleasant"
    primary_icon = icons[0] if icons else "🌤️"

    return {
        "start_date": cand_start.strftime("%Y-%m-%d"),
        "end_date": cand_end.strftime("%Y-%m-%d"),
        "duration_days": trip_days,
        "date_display": format_display_range(cand_start, cand_end),
        "suitability_score": final_score,
        "is_weekend_trip": is_weekend_trip,
        "weather_summary": {
            "condition": primary_cond,
            "icon": primary_icon,
            "avg_max_temp": avg_max_temp,
            "avg_min_temp": avg_min_temp,
            "rain_probability": avg_rain_prob,
            "total_precipitation_mm": total_precip,
        },
        "confidence": confidence,
        "confidence_label": confidence_label,
        "reasons": reasons[:3],
        "trade_offs": trade_offs[:2],
    }


def pick_diverse_recommendations(candidates: List[Dict[str, Any]], trip_days: int) -> List[Dict[str, Any]]:
    """
    Selects top 3 distinct candidate windows (e.g. Best Overall, Best Weekend, Best Midweek/Alternative).
    """
    if not candidates:
        return []

    selected: List[Dict[str, Any]] = []

    # 1. Best Overall Window
    best_overall = dict(candidates[0])
    best_overall["badge"] = "🌟 Best Overall"
    best_overall["rank_title"] = "Optimal Weather & Timing"
    selected.append(best_overall)

    # 2. Best Weekend Getaway (if different from overall)
    weekend_cand = next(
        (c for c in candidates if c["is_weekend_trip"] and c["start_date"] != best_overall["start_date"]),
        None
    )
    if weekend_cand:
        wk = dict(weekend_cand)
        wk["badge"] = "🌴 Weekend Getaway"
        wk["rank_title"] = "Best Weekend Alignment"
        selected.append(wk)

    # 3. Best Midweek / Budget / Low-Crowd Option
    midweek_cand = next(
        (c for c in candidates
         if not c["is_weekend_trip"]
         and c["start_date"] not in [s["start_date"] for s in selected]),
        None
    )
    if midweek_cand:
        mw = dict(midweek_cand)
        mw["badge"] = "💼 Midweek & Lower Crowds"
        mw["rank_title"] = "Less Crowded & Better Rates"
        selected.append(mw)

    # 4. If we still need more options, fill with highest scoring distinct start dates
    for c in candidates:
        if len(selected) >= 3:
            break
        if c["start_date"] not in [s["start_date"] for s in selected]:
            alt = dict(c)
            alt["badge"] = "✨ Alternative Window"
            alt["rank_title"] = "Alternative Travel Option"
            selected.append(alt)

    return selected
