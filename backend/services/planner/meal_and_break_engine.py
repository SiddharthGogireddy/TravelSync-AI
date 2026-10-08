import math
from typing import Dict, List, Optional, Any, Tuple


# Default dining presets if no local restaurant is found in OSM pool
FALLBACK_CUISINES = {
    "breakfast": [
        {"name": "Sunrise Cafe & Bakery", "cuisine": "Artisan Coffee & Fresh Pastries", "price": 250},
        {"name": "Local Heritage Breakfast Point", "cuisine": "Traditional Morning Specialties", "price": 180},
        {"name": "The Morning Roast", "cuisine": "Continental & Healthy Bowls", "price": 320},
    ],
    "lunch": [
        {"name": "Grand Spice Restaurant", "cuisine": "Authentic Regional Cuisine", "price": 500},
        {"name": "The Green Leaf Veg Bistro", "cuisine": "Farm-to-Table Vegetarian", "price": 420},
        {"name": "Coastline Seafood & Grill", "cuisine": "Fresh Catch & Coastal Curries", "price": 680},
    ],
    "dinner": [
        {"name": "Amber Glow Fine Dining", "cuisine": "Gourmet Multi-Cuisine & Wine", "price": 950},
        {"name": "Breezy Rooftop Lounge", "cuisine": "Tandoori Specialties & Cocktails", "price": 850},
        {"name": "Heritage Garden Restaurant", "cuisine": "Classic Regional Thalis & Grills", "price": 600},
    ],
}


def find_nearest_food_place(
    reference_lat: float,
    reference_lon: float,
    available_places: List[Dict[str, Any]],
    excluded_names: set,
    meal_type: str = "lunch",
    preferred_budget_tier: str = "Medium",
    dietary_preference: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Finds the closest food establishment from the candidate pool matching
    budget tier and dietary preference.
    """
    candidates = []

    for p in available_places:
        name = p.get("name", "").strip()
        cat = (p.get("category") or "").lower()
        if not name or name.lower() in excluded_names:
            continue

        # Check if it is a food venue
        is_food = any(
            k in cat or k in name.lower()
            for k in ["food", "restaurant", "cafe", "dhaba", "dining", "bar", "bistro", "bakery", "kitchen"]
        )
        if not is_food:
            continue

        # Calculate distance to reference attraction
        plat = p.get("lat") or reference_lat
        plon = p.get("lon") or reference_lon
        dlat = (plat - reference_lat) * 111.0
        dlon = (plon - reference_lon) * 111.0 * math.cos(math.radians(reference_lat))
        dist_km = math.sqrt(dlat * dlat + dlon * dlon)

        candidates.append((dist_km, p))

    candidates.sort(key=lambda x: x[0])

    # Filter for vegetarian/dietary if requested
    if dietary_preference and "veg" in dietary_preference.lower():
        veg_candidates = [
            c for c in candidates
            if any(k in c[1].get("name", "").lower() or k in (c[1].get("category") or "").lower() for k in ["veg", "pure veg", "green", "udupi"])
        ]
        if veg_candidates:
            candidates = veg_candidates

    if candidates:
        chosen_dist, chosen_place = candidates[0]
        c_name = chosen_place.get("name")
        c_cat = chosen_place.get("category", "Restaurant")
        
        # Estimate cost based on budget tier
        if preferred_budget_tier.lower() == "low":
            cost = 200 if meal_type == "breakfast" else 350
            tier = "Budget Friendly ($)"
        elif preferred_budget_tier.lower() == "high":
            cost = 550 if meal_type == "breakfast" else 1100
            tier = "Fine Dining ($$$)"
        else:
            cost = 320 if meal_type == "breakfast" else 650
            tier = "Moderate ($$)"

        dietary_tags = ["Vegetarian Options"]
        if "veg" in c_name.lower() or "veg" in c_cat.lower():
            dietary_tags = ["Pure Vegetarian", "Plant-Based"]
        elif any(k in c_name.lower() for k in ["fish", "sea", "crab", "coastal"]):
            dietary_tags = ["Seafood", "Non-Veg"]

        return {
            "name": c_name,
            "cuisine": c_cat or "Local Specialties",
            "distance_km": round(chosen_dist, 2),
            "estimated_cost_per_person": cost,
            "price_tier": tier,
            "dietary_tags": dietary_tags,
            "is_custom_selected": True,
        }

    # Fallback preset
    preset_idx = (abs(int(reference_lat * 100)) % len(FALLBACK_CUISINES[meal_type]))
    preset = FALLBACK_CUISINES[meal_type][preset_idx]
    
    tier_label = "Budget ($)" if preferred_budget_tier.lower() == "low" else ("Fine Dining ($$$)" if preferred_budget_tier.lower() == "high" else "Moderate ($$)")
    multiplier = 0.7 if preferred_budget_tier.lower() == "low" else (1.6 if preferred_budget_tier.lower() == "high" else 1.0)
    
    return {
        "name": preset["name"],
        "cuisine": preset["cuisine"],
        "distance_km": 0.5,
        "estimated_cost_per_person": int(preset["price"] * multiplier),
        "price_tier": tier_label,
        "dietary_tags": ["Vegetarian Options", "Regional Delicacies"],
        "is_custom_selected": False,
    }


def plan_day_meals_and_breaks(
    day_places: List[Dict[str, Any]],
    available_places: List[Dict[str, Any]],
    day_index: int,
    travelers: Optional[List[Dict[str, Any]]] = None,
    total_day_distance_km: float = 0.0,
) -> Dict[str, Any]:
    """
    Generates balanced meal recommendations (breakfast, lunch, dinner)
    and rest pauses tailored to the day's attractions and travelers.
    """
    used_names = set()
    traveler_budget = "Medium"
    dietary_pref = None

    if travelers and len(travelers) > 0:
        traveler_budget = travelers[0].get("budget", "Medium")
        # Check interests for food/veg
        all_interests = []
        for t in travelers:
            all_interests.extend(t.get("interests", []))
        if any("veg" in i.lower() for i in all_interests):
            dietary_pref = "Vegetarian"

    # Reference points
    first_place = day_places[0] if day_places else {}
    mid_idx = len(day_places) // 2 if day_places else 0
    mid_place = day_places[mid_idx] if day_places else {}
    last_place = day_places[-1] if day_places else {}

    ref_lat = first_place.get("lat", 15.2993)
    ref_lon = first_place.get("lon", 74.1240)

    # 1. Breakfast (08:15 AM - 09:15 AM)
    b_lat = first_place.get("lat", ref_lat)
    b_lon = first_place.get("lon", ref_lon)
    breakfast = find_nearest_food_place(
        b_lat, b_lon, available_places, used_names, "breakfast", traveler_budget, dietary_pref
    )
    breakfast["meal_type"] = "Breakfast"
    breakfast["time_slot"] = "08:15 AM - 09:15 AM"
    breakfast["near_location"] = first_place.get("name", "Day Start")
    used_names.add(breakfast["name"].lower())

    # 2. Lunch (01:00 PM - 02:00 PM)
    l_lat = mid_place.get("lat", ref_lat)
    l_lon = mid_place.get("lon", ref_lon)
    lunch = find_nearest_food_place(
        l_lat, l_lon, available_places, used_names, "lunch", traveler_budget, dietary_pref
    )
    lunch["meal_type"] = "Lunch"
    lunch["time_slot"] = "01:00 PM - 02:00 PM"
    lunch["near_location"] = mid_place.get("name", "Midday Location")
    used_names.add(lunch["name"].lower())

    # 3. Dinner (08:00 PM - 09:30 PM)
    d_lat = last_place.get("lat", ref_lat)
    d_lon = last_place.get("lon", ref_lon)
    dinner = find_nearest_food_place(
        d_lat, d_lon, available_places, used_names, "dinner", traveler_budget, dietary_pref
    )
    dinner["meal_type"] = "Dinner"
    dinner["time_slot"] = "08:00 PM - 09:30 PM"
    dinner["near_location"] = last_place.get("name", "Evening Destination")
    used_names.add(dinner["name"].lower())

    # 4. Rest Breaks (for long travel days or heavy activity schedules)
    rest_breaks = []
    # Trigger rest break if more than 2 attractions or distance > 15 km
    if len(day_places) >= 2 or total_day_distance_km >= 15.0:
        rest_breaks.append({
            "break_type": "Afternoon Refreshment & Rest Break",
            "time_slot": "04:00 PM - 04:45 PM",
            "duration_minutes": 45,
            "recommended_activity": "Hydrate at a local shaded tea stall, unwind, and rest feet between attractions.",
            "reason": "Replenish energy after midday exploration and transit.",
            "location_context": f"Near {mid_place.get('name', 'central sights')}",
        })

    if total_day_distance_km > 30.0:
        rest_breaks.append({
            "break_type": "Scenic Transit Rest Stop",
            "time_slot": "11:15 AM - 11:35 AM",
            "duration_minutes": 20,
            "recommended_activity": "Stretch legs, grab refreshments, and take panoramic route photos.",
            "reason": "Long travel distance comfort pause.",
            "location_context": "Mid-transit waypoint",
        })

    return {
        "day": day_index,
        "meals": [breakfast, lunch, dinner],
        "rest_breaks": rest_breaks,
        "total_estimated_meal_cost": (
            breakfast["estimated_cost_per_person"]
            + lunch["estimated_cost_per_person"]
            + dinner["estimated_cost_per_person"]
        ),
    }


def attach_meals_and_breaks_to_itinerary(
    day_schedule: Dict[str, List[Dict[str, Any]]],
    available_places: List[Dict[str, Any]],
    travelers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Computes and structures daily dining and rest break recommendations
    for every day in the trip schedule.
    """
    daily_schedule_meals: Dict[str, Any] = {}

    for day_str, places in day_schedule.items():
        try:
            day_num = int(day_str)
        except Exception:
            day_num = 1

        day_distance = sum(p.get("travel_from_previous_km", 0.0) or 0.0 for p in places)
        day_meals_info = plan_day_meals_and_breaks(
            day_places=places,
            available_places=available_places,
            day_index=day_num,
            travelers=travelers,
            total_day_distance_km=day_distance,
        )
        daily_schedule_meals[day_str] = day_meals_info

    return daily_schedule_meals
