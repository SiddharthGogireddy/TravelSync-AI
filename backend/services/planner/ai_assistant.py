import re
from typing import Dict, List, Optional, Any, Tuple
from backend.services.gemini_service import generate


LOCAL_FOOD_GUIDE = {
    "goa": ["Goan Fish Curry Thali", "Chicken Cafreal with Poi", "Prawn Balchao", "Bebinca dessert", "Feni & Kokum Cooler"],
    "bengaluru": ["Crispy Benne Masala Dosa", "Traditional Filter Coffee", "Bisi Bele Bath", "Mangalore Buns", "Mysore Pak"],
    "hyderabad": ["Hyderabadi Dum Biryani", "Mirchi Ka Salan", "Double Ka Meetha", "Irani Chai with Osmania Biscuits", "Pathar Ka Gosht"],
    "mysuru": ["Authentic Mysore Masala Dosa", "Mylari Dosa", "Mysore Pak from Guru Sweets", "Filter Coffee", "Chiroti"],
    "mumbai": ["Vada Pav & Pav Bhaji", "Bombil Fry (Bombay Duck)", "Parsi Berry Pulao", "Cutting Chai", "Misal Pav"],
    "delhi": ["Old Delhi Chole Bhature", "Classic Butter Chicken", "Paranthe Wali Gali paranthas", "Kulfi Falooda", "Aloo Tikki"],
    "jaipur": ["Dal Baati Churma", "Pyaaz Kachori from Rawat", "Laal Maas", "Ghewar", "Ker Sangri"],
}


def answer_trip_question(
    trip_data: Dict[str, Any],
    message: str,
) -> Dict[str, Any]:
    """
    Trip-aware Copilot reasoning engine. Generates contextual answers based on
    destination, daily schedule, weather, budget, and traveler preferences.
    """
    msg_lower = message.lower().strip()

    destination = str(trip_data.get("destination", "your destination")).strip()
    dest_key = destination.split(",")[0].strip().lower()
    days = trip_data.get("days", 3)
    travelers = trip_data.get("travelers", [])
    t_count = len(travelers) or 1
    budget = trip_data.get("budget", {})
    remaining = budget.get("remaining", 0)
    budget_status = budget.get("status", "On Budget")
    transport = trip_data.get("transport", {})
    mode = trip_data.get("travel_mode", transport.get("mode", "car"))
    weather_list = trip_data.get("weather", [])
    primary_weather = weather_list[0].get("condition", "Pleasant") if weather_list else "Pleasant"

    # Gather scheduled attraction names
    day_sched = trip_data.get("day_schedule", {})
    all_places = [p.get("name", "") for d in day_sched.values() if isinstance(d, list) for p in d]
    places_str = ", ".join(all_places[:5]) if all_places else "top regional highlights"

    # 1. PACKING ADVICE
    if any(k in msg_lower for k in ["pack", "what to wear", "clothing", "luggage", "dress code", "bag"]):
        topic = "packing"
        rain_likely = any("rain" in str(w.get("condition", "")).lower() for w in weather_list)
        is_warm = any(w.get("temperature", 25) > 28 for w in weather_list)

        items = [
            "Comfortable walking shoes / sneakers with grip for sightseeing and fort visits.",
            "Breathable lightweight cotton clothing for daytime warmth.",
            "Modest attire (covering shoulders and knees) for temple or heritage monument entry.",
            "Power bank, universal charging adapter, and camera gear.",
            "Personal toiletries, reusable water bottle, and a compact daypack.",
        ]
        if rain_likely:
            items.insert(0, "Compact windproof umbrella and lightweight waterproof jacket or poncho.")
            items.append("Waterproof phone pouch and quick-dry footwear.")
        if is_warm:
            items.insert(1, "Sun protection essentials: SPF 50+ sunscreen, UV sunglasses, and a wide-brim hat.")

        reply = (
            f"Here is your personalized packing checklist for **{destination}** ({days} days, {t_count} traveler(s)):\n\n"
            + "\n".join([f"- **{it}**" for it in items])
            + f"\n\n*Forecast Note:* Weather expects **{primary_weather}**. Traveling by **{mode.upper()}**, so keep essentials in an easily accessible cabin bag!"
        )
        suggestions = ["Top local foods to try", "Safety and cultural etiquette", "Best sunset spot", "Daily schedule summary"]

    # 2. LOCAL FOOD & DINING GUIDE
    elif any(k in msg_lower for k in ["food", "eat", "dish", "restaurant", "cuisine", "taste", "dining", "breakfast", "dinner", "lunch"]):
        topic = "food"
        dishes = None
        for k, items in LOCAL_FOOD_GUIDE.items():
            if k in dest_key or dest_key in k:
                dishes = items
                break

        if not dishes:
            dishes = ["Signature regional curry with steamed bread", "Fresh street snacks at local markets", "Artisanal clay-pot dessert", "Specialty aromatic filter brew"]

        reply = (
            f"Culinary highlights not to miss in **{destination}**:\n\n"
            + "\n".join([f"{idx+1}. **{d}**" for idx, d in enumerate(dishes)])
            + f"\n\n*Dining Tip:* In your itinerary, scheduled attractions like {places_str} have vibrant dining clusters nearby. "
            f"Plan lunch between 12:30 PM - 2:00 PM for the freshest preparation!"
        )
        suggestions = ["What should I pack?", "Best sunset viewpoint", "Safety tips & cultural etiquette", "Trip budget overview"]

    # 3. TIMING & SUNSET SPOTS
    elif any(k in msg_lower for k in ["timing", "sunset", "sunrise", "best time", "hours", "when to visit"]):
        topic = "timing"
        first_place = all_places[0] if all_places else "the primary attraction"
        reply = (
            f"**Optimal Timing & Sunset Guide for {destination}:**\n\n"
            f"- **Morning Window (8:00 AM – 10:30 AM):** Best for outdoor heritage sites and temples before midday heat. Ideal for `{first_place}`.\n"
            f"- **Afternoon Window (12:30 PM – 3:30 PM):** Retreat into air-conditioned museums, shaded cafes, or indoor art centers.\n"
            f"- **Golden Hour & Sunset (4:45 PM – 6:30 PM):** Unbeatable lighting for photography! Head to elevated viewpoints, waterfront promenades, or open hilltop fortresses.\n"
            f"- **Evening Pacing:** Unwind with dinner by 8:00 PM to keep your {days}-day rhythm fresh."
        )
        suggestions = ["What local food should I try?", "Packing advice", "How is our budget doing?", "Safety etiquette"]

    # 4. SAFETY & LOCAL ETIQUETTE
    elif any(k in msg_lower for k in ["safe", "etiquette", "culture", "tip", "scam", "dress", "rule", "custom"]):
        topic = "etiquette"
        reply = (
            f"**Local Etiquette & Travel Safety for {destination}:**\n\n"
            f"- **Sacred Sites:** Remove footwear before entering temples/shrines. Keep a scarf handy to cover heads if requested.\n"
            f"- **Hydration:** Drink sealed bottled or filtered water; stay well-hydrated throughout outdoor circuits.\n"
            f"- **Transit:** Use app-based cabs (Uber/Ola) or agree on meter rates beforehand for local auto-rickshaws.\n"
            f"- **Cash & UPI:** Digital payments (UPI/cards) are widely accepted, but retain ₹1,000–₹2,000 in cash for small roadside vendors and entry tokens.\n"
            f"- **Bargaining:** Respectful polite negotiation is common at street souvenir bazaars, usually 15-25% below initial quoted rates."
        )
        suggestions = ["What should I pack?", "Top dishes to try", "Optimal timing advice", "Can we adjust our schedule?"]

    # 5. BUDGET OVERVIEW & SAVINGS
    elif any(k in msg_lower for k in ["budget", "cost", "money", "expensive", "spend", "saving", "rupee", "inr"]):
        topic = "budget"
        hotel_cost = budget.get("categories", {}).get("hotel", 0)
        food_cost = budget.get("categories", {}).get("food", 0)
        reply = (
            f"**Trip Financial Snapshot for {destination}:**\n\n"
            f"- **Total Budget:** ₹{budget.get('total_budget', 0):,}\n"
            f"- **Estimated Spend:** ₹{budget.get('estimated_cost', 0):,}\n"
            f"- **Remaining Balance:** ₹{remaining:,} (*Status: {budget_status}*)\n"
            f"- **Key Categories:** Hotel: ₹{hotel_cost:,} | Food: ₹{food_cost:,} | Transport: ₹{budget.get('categories', {}).get('transport', 0):,}\n\n"
            f"💡 *Assistant Tip:* You can use the **Smart Budget Reallocation** card on this page to dynamically adjust surplus funds into fine dining or activities with one click!"
        )
        suggestions = ["What should I pack?", "Top dishes to try", "Safety & local tips", "Best sunset spot"]

    # 6. ITINERARY & SUMMARY OVERVIEW
    else:
        topic = "general"
        reply = (
            f"Hello! I am your **TravelSync AI Assistant** for your {days}-day trip to **{destination}**.\n\n"
            f"- **Travelers:** {t_count} traveler(s)\n"
            f"- **Transit Mode:** {mode.title()}\n"
            f"- **Weather Forecast:** {primary_weather}\n"
            f"- **Top Itinerary Highlights:** {places_str}\n\n"
            f"How can I help you today? You can ask me about packing checklists, famous regional delicacies, "
            f"safety tips, sunset viewpoints, or budget suggestions!"
        )
        suggestions = ["What should I pack?", "What are the best local foods?", "Best timing & sunset spot", "Safety & cultural etiquette"]

    return {
        "reply": reply,
        "topic": topic,
        "suggested_actions": suggestions,
        "trip_highlights": {
            "destination": destination,
            "days": days,
            "travelers_count": t_count,
            "travel_mode": mode,
            "primary_weather": primary_weather,
            "budget_status": budget_status,
            "remaining_budget": remaining,
        },
    }
