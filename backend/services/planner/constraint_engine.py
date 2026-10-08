import re
from typing import Dict, List, Optional, Tuple, Any


def validate_constraints(constraints: Any) -> Any:
    """
    Validates user constraints and flags impossible or contradicting parameters.
    """
    if not constraints:
        return {"valid": True, "errors": []} if not isinstance(constraints, tuple) else (True, [])

    if hasattr(constraints, "dict"):
        c_dict = constraints.dict()
    elif isinstance(constraints, dict):
        c_dict = constraints
    else:
        c_dict = {}

    errors = []

    # 1. max_daily_distance_km
    max_dist = c_dict.get("max_daily_distance_km")
    if max_dist is not None:
        if not isinstance(max_dist, (int, float)) or max_dist <= 0:
            errors.append("Maximum daily travel distance must be a positive number (km).")

    # 2. max_budget
    max_budget = c_dict.get("max_budget")
    if max_budget is not None:
        if not isinstance(max_budget, (int, float)) or max_budget <= 0:
            errors.append("Maximum budget must be greater than zero.")

    # 3. min_attractions_per_day
    min_attr = c_dict.get("min_attractions_per_day")
    if min_attr is not None:
        if not isinstance(min_attr, int) or min_attr < 0 or min_attr > 10:
            errors.append("Minimum attractions per day must be an integer between 0 and 10.")

    # 4. Check conflict between must_visit and locations_to_avoid
    raw_must = c_dict.get("must_visit_locations") or c_dict.get("must_visit") or []
    raw_avoid = c_dict.get("locations_to_avoid") or c_dict.get("avoided_locations") or []

    must_visits = [str(x).strip().lower() for x in raw_must if str(x).strip()]
    avoid_locs = [str(x).strip().lower() for x in raw_avoid if str(x).strip()]

    direct_conflicts = set(must_visits).intersection(set(avoid_locs))
    if direct_conflicts:
        errors.append(f"Contradicting constraints: '{', '.join(direct_conflicts)}' is specified in both must-visit and avoided locations.")

    # Return a structure that works both as tuple unpacking (is_valid, errors) and dict subscription res["valid"]
    class ValidationResult(dict):
        def __iter__(self):
            yield self["valid"]
            yield self["errors"]

    return ValidationResult(valid=(len(errors) == 0), errors=errors)



def filter_avoided_locations(places: List[Dict[str, Any]], locations_to_avoid: Optional[List[str]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Hard constraint: excludes attractions matching avoided keywords, places, or categories.
    """
    if not locations_to_avoid:
        return places, []

    avoid_keywords = [a.strip().lower() for a in locations_to_avoid if a.strip()]
    if not avoid_keywords:
        return places, []

    allowed = []
    excluded = []

    for place in places:
        name_lower = place.get("name", "").lower()
        cat_lower = place.get("category", "").lower()

        is_avoided = any(
            kw in name_lower or kw in cat_lower or name_lower in kw
            for kw in avoid_keywords
        )

        if is_avoided:
            excluded.append(place)
        else:
            allowed.append(place)

    return allowed, excluded


def evaluate_constraints_satisfaction(
    schedule: Dict[str, List[Dict[str, Any]]],
    budget: Dict[str, Any],
    constraints: Optional[Dict[str, Any]],
    mandatory_visits: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluates whether all planning constraints were satisfied and explains any violations.
    """
    if not constraints:
        return {
            "all_satisfied": True,
            "satisfied_constraints": ["No custom constraints specified"],
            "unsatisfied_constraints": [],
            "explanations": [],
            "conflicts_detected": [],
            "daily_distance_audit": {},
        }

    satisfied = []
    unsatisfied = []
    explanations = []
    conflicts = []
    daily_distances = {}

    # 1. Audit Daily Distance Constraint
    max_dist = constraints.get("max_daily_distance_km")
    if max_dist is not None:
        dist_violated = False
        for day, places in schedule.items():
            day_km = sum(p.get("travel_from_previous_km", 0) or 0 for p in places)
            daily_distances[day] = round(day_km, 2)
            if day_km > max_dist:
                dist_violated = True
                unsatisfied.append(f"max_daily_distance_km on Day {day}")
                explanations.append(
                    f"Day {day} travel distance ({round(day_km, 1)} km) exceeded the maximum limit of {max_dist} km."
                )
        if not dist_violated:
            satisfied.append(f"Max daily travel distance (<= {max_dist} km)")
    else:
        for day, places in schedule.items():
            day_km = sum(p.get("travel_from_previous_km", 0) or 0 for p in places)
            daily_distances[day] = round(day_km, 2)

    # 2. Audit Budget Constraint
    max_b = constraints.get("max_budget")
    if max_b is not None:
        estimated_cost = budget.get("estimated_cost", 0)
        if estimated_cost > max_b:
            unsatisfied.append("max_budget")
            explanations.append(
                f"Estimated trip cost (INR {estimated_cost:,.2f}) exceeded the user constraint of INR {max_b:,.2f}."
            )
        else:
            satisfied.append(f"Maximum budget capped at INR {max_b:,.2f}")

    # 3. Audit Minimum Attractions Per Day Constraint
    min_attr = constraints.get("min_attractions_per_day")
    if min_attr is not None:
        attr_violated = False
        for day, places in schedule.items():
            if len(places) < min_attr:
                attr_violated = True
                unsatisfied.append(f"min_attractions_per_day on Day {day}")
                explanations.append(
                    f"Day {day} only scheduled {len(places)} attraction(s), which is less than the requested minimum of {min_attr}."
                )
        if not attr_violated:
            satisfied.append(f"Minimum {min_attr} attractions per day")

    # 4. Audit Locations to Avoid
    avoid_locs = list(constraints.get("locations_to_avoid") or constraints.get("avoided_locations") or [])
    leaked_avoided = []
    if avoid_locs:
        scheduled_names = [p["name"].lower() for day_places in schedule.values() for p in day_places]
        leaked_avoided = [kw for kw in avoid_locs if any(str(kw).lower() in name for name in scheduled_names)]
        if leaked_avoided:
            unsatisfied.append(f"Avoided locations: {', '.join(leaked_avoided)}")
            explanations.append(f"Locations matching avoided list appeared in schedule: {', '.join(leaked_avoided)}")
        else:
            satisfied.append(f"Excluded {len(avoid_locs)} avoided location(s)")

    # 5. Audit Must-Visit Locations
    raw_must = constraints.get("must_visit_locations") or constraints.get("must_visit") or []
    all_must = list(raw_must)
    if mandatory_visits:
        for v in mandatory_visits:
            v_name = v.get("name") if isinstance(v, dict) else getattr(v, "name", str(v))
            if v_name and v_name not in all_must:
                all_must.append(v_name)

    missing_must = []
    if all_must:
        scheduled_names = [p["name"].lower() for day_places in schedule.values() for p in day_places]
        missing_must = [m for m in all_must if not any(str(m).lower() in name for name in scheduled_names)]
        if missing_must:
            unsatisfied.append(f"Must-visit locations: {', '.join(missing_must)}")
            explanations.append(f"Could not fit mandatory location(s) into itinerary: {', '.join(missing_must)}")
        else:
            satisfied.append(f"Satisfied all {len(all_must)} must-visit location(s)")

    all_ok = len(unsatisfied) == 0

    return {
        "valid": all_ok,
        "all_satisfied": all_ok,
        "violations": unsatisfied,
        "warnings": [],
        "satisfied": {
            "budget": (max_b is None or estimated_cost <= max_b) if max_b is not None else True,
            "distance": (not dist_violated) if max_dist is not None else True,
            "must_visit": len(missing_must) == 0,
            "avoided_locations": len(leaked_avoided) == 0,
        },
        "details": {
            "max_budget": max_b,
            "estimated_total_cost": budget.get("estimated_cost", 0) if budget else 0,
            "max_daily_distance_km": max_dist,
            "max_observed_day_distance_km": max(daily_distances.values()) if daily_distances else 0,
            "must_visit_requested": all_must,
            "must_visit_included": [m for m in all_must if m not in missing_must],
            "must_visit_missing": missing_must,
            "avoided_locations_excluded": [a for a in avoid_locs if a not in leaked_avoided],
            "avoided_locations_violated": leaked_avoided,
        },
        "satisfied_constraints": satisfied,
        "unsatisfied_constraints": unsatisfied,
        "explanations": explanations,
        "explanation": " | ".join(explanations) if explanations else "All user planning constraints were successfully satisfied.",
        "conflicts_detected": conflicts,
        "daily_distance_audit": daily_distances,
    }


evaluate_constraints = evaluate_constraints_satisfaction

