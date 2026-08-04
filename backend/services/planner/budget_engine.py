BUDGET_RULES = {

    "Budget": {
        "hotel": "Hostel or Budget Hotel",
        "transport": "Bus or Scooter",
        "food": "Street Food and Local Cafes",
        "activity": "Free Attractions"
    },

    "Medium": {
        "hotel": "3-Star Hotel",
        "transport": "Rental Car or Taxi",
        "food": "Popular Restaurants",
        "activity": "Paid Attractions"
    },

    "Luxury": {
        "hotel": "5-Star Resort",
        "transport": "Private Cab",
        "food": "Fine Dining",
        "activity": "Premium Experiences"
    }

}
def get_budget_rules(budget):

    return BUDGET_RULES.get(
        budget,
        BUDGET_RULES["Medium"]
    )