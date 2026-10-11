from backend.services.planner.budget_constants import (
    HOTEL_COST,
    FOOD_COST,
    ACTIVITY_COST,
    TRANSPORT_COST,
    EMERGENCY_PERCENT,
)


def calculate_budget(
    travelers,
    days,
    travel_mode,
    hotels,
    places,
    scheduled_activity_count=None,
    total_budget=None,
    custom_transport_cost=None,
):
    days = max(1, int(days) if days else 1)
    traveler_count = max(1, len(travelers) if travelers else 1)

    # Resolve true scheduled activity count
    if scheduled_activity_count is not None:
        activity_count = max(0, int(scheduled_activity_count))
    elif isinstance(places, dict):
        activity_count = sum(len(v) for v in places.values() if isinstance(v, list))
    elif isinstance(places, list):
        # If passed the full candidate pool rather than scheduled items, cap to expected itinerary capacity
        if len(places) > days * 4:
            activity_count = days * 3
        else:
            activity_count = len(places)
    else:
        activity_count = days * 3

    # Resolve transport pricing
    mode_key = str(travel_mode).lower().strip()
    if custom_transport_cost is not None and custom_transport_cost > 0:
        overall_transport_cost = round(float(custom_transport_cost))
        transport_per_person = round(overall_transport_cost / traveler_count)
    else:
        transport_unit = TRANSPORT_COST.get(mode_key, 1000)
        transport_per_person = transport_unit * days
        overall_transport_cost = transport_per_person * traveler_count

    hotel_cost = 0
    food_cost = 0
    transport_cost = 0
    activity_cost = 0
    per_person = []

    # If travelers is empty, synthesize a default profile
    safe_travelers = travelers if travelers and len(travelers) > 0 else [{"name": "Traveler 1", "budget": "Medium"}]

    for traveler in safe_travelers:
        budget_tier = traveler.get("budget", "Medium")

        hotel = HOTEL_COST.get(budget_tier, 2500) * days
        food = FOOD_COST.get(budget_tier, 800) * days
        activities = round((ACTIVITY_COST.get(budget_tier, 700) * activity_count) / traveler_count)
        transport = transport_per_person

        share = hotel + food + activities + transport

        hotel_cost += hotel
        food_cost += food
        activity_cost += activities
        transport_cost += transport

        per_person.append(
            {
                "name": traveler.get("name", "Traveler"),
                "share": round(share),
            }
        )

    # Use overall_transport_cost to guarantee exact consistency if custom override was passed
    if custom_transport_cost is not None and custom_transport_cost > 0:
        transport_cost = overall_transport_cost

    subtotal = hotel_cost + food_cost + transport_cost + activity_cost
    emergency = round(subtotal * EMERGENCY_PERCENT)
    estimated_total = subtotal + emergency

    # If total budget was not explicitly defined by user, planned budget is initialized to cover the full estimate
    if total_budget is None:
        total_budget = estimated_total
        remaining = 0
        status = "Near Budget"
        # Proportionately adjust per_person shares so sum matches total planned budget
        for person in per_person:
            person["share"] = round(person["share"] * (1.0 + EMERGENCY_PERCENT))
    else:
        total_budget = round(float(total_budget))
        remaining = total_budget - estimated_total
        if total_budget > 0:
            if remaining > total_budget * 0.15:
                status = "Under Budget"
            elif remaining >= 0:
                status = "Near Budget"
            else:
                status = "Over Budget"
        else:
            status = "Near Budget"

    average_per_person = round(estimated_total / traveler_count)
    average_per_day = round(estimated_total / days)
    category_total = max(1, estimated_total)

    budget_utilization_pct = (
        round((estimated_total / total_budget) * 100, 1) if total_budget > 0 else 100.0
    )

    return {
        "total_budget": total_budget,
        "estimated_cost": estimated_total,
        "remaining": remaining,
        "status": status,
        "average_per_day": average_per_day,
        "average_per_person": average_per_person,
        "budget_utilization_pct": budget_utilization_pct,
        "categories": {
            "hotel": round(hotel_cost),
            "food": round(food_cost),
            "transport": round(transport_cost),
            "activities": round(activity_cost),
            "emergency": round(emergency),
        },
        "category_percentage": {
            "hotel": round(hotel_cost / category_total * 100),
            "food": round(food_cost / category_total * 100),
            "transport": round(transport_cost / category_total * 100),
            "activities": round(activity_cost / category_total * 100),
            "emergency": round(emergency / category_total * 100),
        },
        "per_person": per_person,
    }