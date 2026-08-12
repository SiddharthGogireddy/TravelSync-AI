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
):
    hotel_cost = 0
    food_cost = 0
    transport_cost = 0
    activity_cost = 0

    per_person = []

    for traveler in travelers:

        budget = traveler["budget"]

        hotel = HOTEL_COST.get(budget, 2500) * days
        food = FOOD_COST.get(budget, 800) * days
        activities = ACTIVITY_COST.get(budget, 700) * len(places)
        transport = (
            TRANSPORT_COST.get(travel_mode, 1000)
            * days
        )

        share = hotel + food + activities + transport

        hotel_cost += hotel
        food_cost += food
        activity_cost += activities
        transport_cost += transport

        per_person.append(
            {
                "name": traveler["name"],
                "share": round(share),
            }
        )

    subtotal = (
        hotel_cost
        + food_cost
        + transport_cost
        + activity_cost
    )

    emergency = round(
        subtotal * EMERGENCY_PERCENT
    )

    estimated_total = subtotal + emergency

    total_budget = sum(
        person["share"]
        for person in per_person
    )

    remaining = total_budget - estimated_total

    if remaining > estimated_total * 0.20:
        status = "Under Budget"
    elif remaining >= 0:
        status = "Near Budget"
    else:
        status = "Over Budget"

    traveler_count = max(1, len(travelers))

    average_per_person = round(
        estimated_total / traveler_count
    )

    average_per_day = round(
        estimated_total / max(1, days)
    )

    category_total = max(1, estimated_total)

    return {
        "total_budget": round(total_budget),
        "estimated_cost": round(estimated_total),
        "remaining": round(remaining),
        "status": status,
        "average_per_day": average_per_day,
        "average_per_person": average_per_person,
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