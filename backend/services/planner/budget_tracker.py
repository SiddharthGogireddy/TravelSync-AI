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
    total_budget = 0

    hotel_cost = 0
    food_cost = 0
    transport_cost = 0
    activity_cost = 0

    per_person = []

    for traveler in travelers:

        budget = traveler["budget"]

        hotel_cost += HOTEL_COST.get(budget, 2500) * days

        food_cost += FOOD_COST.get(budget, 800) * days

        activity_cost += (
            ACTIVITY_COST.get(budget, 700)
            * len(places)
        )

        transport_cost += TRANSPORT_COST.get(
            travel_mode,
            1000
        ) * days

        estimated = (
            HOTEL_COST.get(budget, 2500) * days
            + FOOD_COST.get(budget, 800) * days
            + ACTIVITY_COST.get(budget, 700) * len(places)
            + TRANSPORT_COST.get(travel_mode, 1000) * days
        )

        total_budget += estimated

        per_person.append(
            {
                "name": traveler["name"],
                "share": estimated,
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

    return {
        "total_budget": total_budget,
        "estimated_cost": estimated_total,
        "remaining": total_budget - estimated_total,
        "categories": {
            "hotel": hotel_cost,
            "food": food_cost,
            "transport": transport_cost,
            "activities": activity_cost,
            "emergency": emergency,
        },
        "per_person": per_person,
    }