import math
from typing import Dict, List, Optional, Any, Tuple
from backend.services.planner.transport_planner import build_transport_plan
from backend.services.planner.budget_tracker import calculate_budget


def estimate_mode_metrics(
    mode: str,
    distance_km: float,
    party_size: int = 1,
    luggage: str = "standard",
    budget_tier: str = "moderate",
) -> Dict[str, Any]:
    """
    Computes realistic cost (INR), duration (hours), carbon footprint (kg CO2),
    comfort, and convenience metrics for a given transit mode.
    """
    mode = str(mode).lower().strip()
    distance_km = max(10.0, float(distance_km))
    party_size = max(1, int(party_size))
    luggage = str(luggage).lower().strip()

    if mode == "car":
        # Group fuel (avg 14 km/l @ Rs 100/l = ~Rs 7.2/km) + Tolls (~Rs 1.8/km) + Vehicle base rental/driver (Rs 1200)
        fuel_and_toll = distance_km * 9.0
        base_fee = 1400.0
        total_cost = round(fuel_and_toll + base_fee)
        duration = round(max(1.0, distance_km / 55.0), 1)
        carbon_kg = round(distance_km * 0.14, 1)
        comfort = 8.5
        convenience = 9.2
        viable = True
        suitability_reason = "Flexible door-to-door drive with generous trunk space, great for groups."

    elif mode == "train":
        # Per-person railway ticket (Base 300 + 1.35/km for 3AC/Express)
        cost_per_person = 320.0 + (distance_km * 1.35)
        total_cost = round(cost_per_person * party_size)
        # Train transit speed ~65 km/h + 1.2h station buffer & boarding
        duration = round((distance_km / 65.0) + 1.2, 1)
        carbon_kg = round(distance_km * 0.035 * party_size, 1)
        comfort = 8.8
        convenience = 7.8
        viable = True
        suitability_reason = "Relaxing, spacious journey with lowest carbon footprint and city-center access."

    elif mode == "flight":
        if distance_km < 180.0:
            viable = False
            total_cost = round(3500 * party_size + 1500)
            duration = 3.5
            carbon_kg = round(distance_km * 0.22 * party_size, 1)
            comfort = 6.0
            convenience = 4.0
            suitability_reason = "Not practical for short distances; airport check-in exceeds driving time."
        else:
            viable = True
            # Base airfare Rs 2800 + Rs 3.6/km per person + Rs 1200 combined airport cabs
            airfare_per_person = 2800.0 + (distance_km * 3.6)
            total_cost = round((airfare_per_person * party_size) + 1200.0)
            # Flight time ~650 km/h + 2.8 hours total airport check-in, security & transfers
            flight_time = distance_km / 650.0
            duration = round(flight_time + 2.8, 1)
            carbon_kg = round(distance_km * 0.22 * party_size, 1)
            comfort = 7.5
            convenience = 7.0
            suitability_reason = "Fastest arrival over long distances; best for tight vacation schedules."

    elif mode == "bus":
        # Per person bus ticket (Base 160 + Rs 1.1/km)
        ticket_per_person = 160.0 + (distance_km * 1.1)
        total_cost = round(ticket_per_person * party_size)
        duration = round((distance_km / 45.0) + 0.8, 1)
        carbon_kg = round(distance_km * 0.05 * party_size, 1)
        comfort = 6.0
        convenience = 6.8
        viable = True
        suitability_reason = "Most economical road option with frequent intercity departures."

    else:
        raise ValueError(f"Unknown transport mode: {mode}")

    per_person_cost = round(total_cost / party_size)

    return {
        "mode": mode,
        "viable": viable,
        "total_cost_inr": total_cost,
        "per_person_cost_inr": per_person_cost,
        "duration_hours": duration,
        "carbon_kg": carbon_kg,
        "comfort_score": comfort,
        "convenience_score": convenience,
        "suitability_reason": suitability_reason,
    }


def score_mode_option(
    metrics: Dict[str, Any],
    distance_km: float,
    party_size: int,
    luggage: str,
    budget_tier: str,
    min_cost: float,
    min_duration: float,
) -> float:
    """
    Calculates weighted holistic score (0-100) for a travel mode.
    """
    if not metrics.get("viable", True):
        return 20.0

    # Normalized cost score (lower cost = higher score, 0-35)
    cost_ratio = min_cost / max(1.0, metrics["total_cost_inr"])
    cost_pts = min(35.0, cost_ratio * 35.0)

    # Normalized time score (lower duration = higher score, 0-35)
    time_ratio = min_duration / max(0.5, metrics["duration_hours"])
    time_pts = min(35.0, time_ratio * 35.0)

    # Comfort & Convenience points (0-20)
    comfort_pts = (metrics["comfort_score"] / 10.0) * 10.0
    conv_pts = (metrics["convenience_score"] / 10.0) * 10.0

    # Eco bonus (0-10)
    eco_pts = 10.0 if metrics["mode"] == "train" else (7.0 if metrics["mode"] == "bus" else (4.0 if metrics["mode"] == "car" else 1.0))

    base_score = cost_pts + time_pts + comfort_pts + conv_pts + eco_pts

    # Modifiers based on party size
    if party_size >= 4 and metrics["mode"] == "car":
        base_score += 12.0  # Shared car split across 4+ travelers is immense value
    elif party_size >= 4 and metrics["mode"] == "flight":
        base_score -= 8.0   # 4+ flight tickets becomes very steep

    # Modifiers based on luggage
    if luggage == "heavy":
        if metrics["mode"] in ["car", "train"]:
            base_score += 6.0
        elif metrics["mode"] == "flight":
            base_score -= 6.0  # Excess baggage limits

    # Modifiers based on distance
    if distance_km > 600.0:
        if metrics["mode"] == "flight":
            base_score += 14.0
        elif metrics["mode"] == "bus":
            base_score -= 12.0  # Painful 13+ hour bus ride
    elif distance_km < 140.0:
        if metrics["mode"] == "car":
            base_score += 10.0
        elif metrics["mode"] == "flight":
            base_score -= 30.0

    # Modifiers based on budget tier
    if budget_tier == "budget":
        if metrics["mode"] in ["train", "bus"]:
            base_score += 10.0
        elif metrics["mode"] == "flight":
            base_score -= 15.0
    elif budget_tier == "luxury":
        if metrics["mode"] in ["flight", "car"]:
            base_score += 10.0
        elif metrics["mode"] == "bus":
            base_score -= 15.0

    return round(max(25.0, min(99.0, base_score)), 1)


def generate_transport_recommendations(
    source: str,
    destination: str,
    distance_km: float,
    current_mode: str = "car",
    party_size: int = 1,
    luggage: str = "standard",
    budget_tier: str = "moderate",
) -> Dict[str, Any]:
    """
    Evaluates all major modes and delivers trade-off matrix and top recommendation.
    """
    MODES = ["car", "train", "flight", "bus"]
    evaluated_modes: Dict[str, Any] = {}

    for m in MODES:
        evaluated_modes[m] = estimate_mode_metrics(
            mode=m,
            distance_km=distance_km,
            party_size=party_size,
            luggage=luggage,
            budget_tier=budget_tier,
        )

    # Find min cost & min duration among viable modes
    viable_modes = [m for m in MODES if evaluated_modes[m]["viable"]]
    min_cost = min(evaluated_modes[m]["total_cost_inr"] for m in viable_modes)
    min_duration = min(evaluated_modes[m]["duration_hours"] for m in viable_modes)

    fastest_mode = min(viable_modes, key=lambda m: evaluated_modes[m]["duration_hours"])
    cheapest_mode = min(viable_modes, key=lambda m: evaluated_modes[m]["total_cost_inr"])
    greenest_mode = "train"

    for m in MODES:
        sc = score_mode_option(
            metrics=evaluated_modes[m],
            distance_km=distance_km,
            party_size=party_size,
            luggage=luggage,
            budget_tier=budget_tier,
            min_cost=min_cost,
            min_duration=min_duration,
        )
        evaluated_modes[m]["score"] = sc

        badges = []
        if m == fastest_mode:
            badges.append("⚡ Fastest")
        if m == cheapest_mode:
            badges.append("💰 Most Economical")
        if m == greenest_mode:
            badges.append("🌱 Eco Champion")
        if m == current_mode.lower():
            badges.append("📍 Currently Selected")

        evaluated_modes[m]["badges"] = badges

    # Pick highest scoring mode as top recommendation
    recommended_mode = max(viable_modes, key=lambda m: evaluated_modes[m]["score"])
    evaluated_modes[recommended_mode]["badges"].insert(0, "🌟 Recommended Best Match")

    rec_data = evaluated_modes[recommended_mode]

    # Synthesize recommendation rationale
    rationale_parts = []
    if recommended_mode == fastest_mode and recommended_mode == cheapest_mode:
        rationale_parts.append(f"It is both the fastest ({rec_data['duration_hours']}h) and most affordable (INR {rec_data['total_cost_inr']}).")
    elif recommended_mode == fastest_mode:
        rationale_parts.append(f"It saves maximum transit time ({rec_data['duration_hours']} hours).")
    elif recommended_mode == cheapest_mode:
        rationale_parts.append(f"It provides the lowest total transit cost of INR {rec_data['total_cost_inr']} for {party_size} traveler(s).")
    elif recommended_mode == "car" and party_size >= 3:
        rationale_parts.append(f"With {party_size} travelers, private driving splits fuel/tolls down to ~INR {rec_data['per_person_cost_inr']}/person with door-to-door flexibility.")
    elif recommended_mode == "train":
        rationale_parts.append(f"Optimal balance of spacious comfort ({rec_data['duration_hours']}h), low fares, and zero luggage stress.")
    else:
        rationale_parts.append(rec_data["suitability_reason"])

    recommendation_summary = (
        f"We recommend {recommended_mode.upper()} for this {distance_km} km journey from {source} to {destination}. "
        + " ".join(rationale_parts)
    )

    return {
        "recommended_mode": recommended_mode,
        "recommendation_summary": recommendation_summary,
        "current_mode": current_mode.lower(),
        "is_using_recommended": current_mode.lower() == recommended_mode,
        "distance_km": distance_km,
        "party_size": party_size,
        "luggage": luggage,
        "budget_tier": budget_tier,
        "options": evaluated_modes,
    }


def switch_trip_transport(
    trip_data: Dict[str, Any],
    new_mode: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Switches the trip's travel mode, rebuilds transport legs and recomputes budget.
    """
    new_mode = str(new_mode).lower().strip()
    if new_mode not in ["car", "train", "flight", "bus"]:
        return trip_data, {
            "success": False,
            "error": f"Invalid travel mode '{new_mode}'. Supported: car, train, flight, bus",
        }

    source = trip_data.get("source", "Origin")
    destination = trip_data.get("destination", "Destination")
    route = trip_data.get("route", {})
    dist_km = route.get("distance_km", 200.0)
    dur_hours = route.get("duration_hours", 4.0)

    # 1. Rebuild transport plan
    new_transport_summary = build_transport_plan(
        source=source,
        destination=destination,
        travel_mode=new_mode,
        road_distance_km=dist_km,
        road_duration_hours=dur_hours,
    )
    trip_data["transport"] = new_transport_summary
    trip_data["travel_mode"] = new_mode

    # 2. Recalculate trip budget with new transport mode
    try:
        travelers = trip_data.get("travelers", [])
        days = trip_data.get("days", 3)
        hotels = trip_data.get("hotels", [])
        places = trip_data.get("places", [])
        updated_budget = calculate_budget(
            travelers=travelers,
            days=days,
            travel_mode=new_mode,
            hotels=hotels,
            places=places,
        )
        trip_data["budget"] = updated_budget
    except Exception:
        pass

    # 3. Update dashboard transit metrics
    if "dashboard" in trip_data:
        trip_data["dashboard"]["travel_mode"] = new_mode
        trip_data["dashboard"]["duration"] = new_transport_summary["duration_hours"]

    # 4. Refresh recommendation status
    party_size = len(trip_data.get("travelers", [{}])) or 1
    recs = generate_transport_recommendations(
        source=source,
        destination=destination,
        distance_km=dist_km,
        current_mode=new_mode,
        party_size=party_size,
    )
    trip_data["transport_recommendations"] = recs

    audit = {
        "success": True,
        "previous_mode": recs.get("current_mode"),
        "new_mode": new_mode,
        "new_duration_hours": new_transport_summary["duration_hours"],
        "summary": f"Transport switched to {new_mode.upper()} ({new_transport_summary['duration_hours']} hrs transit).",
    }

    return trip_data, audit
