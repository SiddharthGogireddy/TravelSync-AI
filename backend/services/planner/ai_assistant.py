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

LOCAL_FOOD_PREFERENCES: Dict[str, Dict[str, List[str]]] = {
    "hyderabad": {
        "chicken": [
            "Hyderabadi Chicken Dum Biryani (slow-cooked fragrant basmati rice layered with marinated chicken, saffron, and fried onions)",
            "Chicken 65 (legendary fiery, crispy deep-fried chicken tossed with curry leaves, garlic, and green chilies)",
            "Hyderabadi Dum Ka Chicken (rich, slow-cooked royal delicacy in a velvety cashew, almond, and yogurt gravy)",
            "Tala Hua Chicken (crispy pan-fried Hyderabadi chicken seasoned with zesty aromatic spices)",
            "Hyderabadi Chicken Seekh / Reshmi Kebabs (flame-grilled melt-in-mouth chicken kebabs with mint chutney)",
        ],
        "mutton": [
            "Hyderabadi Mutton Dum Biryani (tender goat meat marinated in spices and slow-cooked with aged basmati rice)",
            "Pathar Ka Gosht (succulent mutton fillets seared on a red-hot granite slab)",
            "Hyderabadi Haleem (slow-simmered rich stew of tender meat, broken wheat, lentils, and pure ghee)",
            "Mutton Boti Kebab with Rumali Roti",
        ],
        "vegetarian": [
            "Mirchi Ka Salan (tangy, nutty curry made with roasted peanuts, sesame seeds, tamarind, and large mild chilies)",
            "Bagara Baingan (baby eggplants gently simmered in a spiced coconut, sesame, and peanut gravy)",
            "Hyderabadi Khatti Dal paired with Steamed Rice and Ghee",
            "Crispy Paneer 65 & Fragrant Bagara Rice",
        ],
        "seafood": [
            "Apollo Fish (famous Hyderabad crispy spiced boneless fish tossed with yogurt, curry leaves, and green chilies)",
            "Tawa Machhli (pan-seared spiced freshwater fish)",
            "Hyderabadi Prawn Masala Roast",
        ],
        "dessert": [
            "Double Ka Meetha (crisp fried bread pudding infused with cardamom syrup, saffron, and rich rabri)",
            "Qubani Ka Meetha (royal Hyderabadi dessert made from stewed Turkish apricots, served with thick cream)",
            "Badam Ki Jhab and Gil-e-Firdaus (traditional rice and almond pudding)",
        ],
        "tea_coffee": [
            "Irani Chai paired with warm Osmania Biscuits or fine butter cookies",
            "Zafrani Irani Chai (aromatic saffron-infused milk tea)",
        ],
    },
    "goa": {
        "chicken": [
            "Chicken Cafreal with crusty local Poi bread",
            "Goan Chicken Xacuti (complex roasted coconut and aromatic spice gravy)",
            "Chicken Vindaloo (tangy, spiced wine vinegar marinated classic)",
        ],
        "seafood": [
            "Goan Fish Curry Thali with Kingfish (Surmai)",
            "Prawn Balchao (fiery, tangy pickled prawn specialty)",
            "Rava Fried Prawns or Calamari",
        ],
        "vegetarian": [
            "Goan Mushroom Xacuti",
            "Khatkhate (traditional Goan mixed vegetable and lentil stew)",
            "Bhendi Sol (okra in tangy kokum curry)",
        ],
        "dessert": [
            "Bebinca (traditional multi-layered Goan coconut milk cake)",
            "Dodol (rich festive dessert of coconut milk and jaggery)",
        ],
    },
    "bengaluru": {
        "chicken": [
            "Bangalore Nagarjuna-style Andhra Chili Chicken",
            "Chicken Donne Biryani (aromatic seeraga samba rice cooked with mint and coriander)",
            "Guntur Chicken Dry",
        ],
        "vegetarian": [
            "Crispy Benne Masala Dosa with coconut chutney and sambar",
            "Bisi Bele Bath with boondi and ghee",
            "Mangalore Buns with spicy coconut chutney",
        ],
        "tea_coffee": [
            "Traditional South Indian Filter Coffee in stainless steel dabara",
        ],
        "dessert": [
            "Authentic Melt-in-Mouth Mysore Pak",
            "Obbattu / Holige (sweet jaggery and lentil flatbread)",
        ],
    },
    "mumbai": {
        "chicken": [
            "Parsi Chicken Dhansak with caramelized brown rice",
            "Colaba-style Chicken Baida Roti",
            "Chicken Malvani Sukka",
        ],
        "vegetarian": [
            "Mumbai Vada Pav & Pav Bhaji with generous butter",
            "Misal Pav with spicy farsan and lime",
            "Sev Puri and Pani Puri from Chowpatty",
        ],
        "seafood": [
            "Bombil Fry (Bombay Duck rava fry)",
            "Kolambi (Prawn) Koliwada",
        ],
        "tea_coffee": [
            "Cutting Chai from historic Irani cafes",
        ],
    },
    "delhi": {
        "chicken": [
            "Classic Old Delhi Butter Chicken (Murgh Makhani)",
            "Daryaganj Tandoori Chicken",
            "Chicken Malai Tikka with roomali roti",
        ],
        "vegetarian": [
            "Old Delhi Chole Bhature with pickled chilies",
            "Paranthe Wali Gali stuffed paranthas",
            "Chandni Chowk Aloo Tikki & Dahi Bhalla",
        ],
        "dessert": [
            "Kuldip / Giani Kulfi Falooda",
            "Hot Jalebi with Rabri from Dariba Kalan",
        ],
    },
    "jaipur": {
        "chicken": [
            "Rajasthani Junglee Murgh (slow-cooked chicken with pure ghee and dry whole red chilies)",
            "Murg Ka Mokul (boneless chicken in almond and yogurt gravy)",
        ],
        "mutton": [
            "Royal Laal Maas (legendary fiery mutton curry prepared with Mathania red chilies)",
            "Safed Maas (delicate mutton in white cashew and poppy seed gravy)",
        ],
        "vegetarian": [
            "Authentic Dal Baati Churma with garlic chutney",
            "Pyaaz Kachori from Rawat Mishthan Bhandar",
            "Ker Sangri (traditional desert berry and bean delicacy)",
        ],
        "dessert": [
            "Paneer Ghewar drenched in saffron syrup",
            "Mawa Kachori from LMB",
        ],
    },
    "mysuru": {
        "vegetarian": [
            "Authentic Mysore Masala Dosa with red chili-garlic chutney",
            "Mylari Dosa with white butter",
            "Shavige Bath and Chiroti",
        ],
        "dessert": [
            "Original Mysore Pak from Guru Sweets Mart",
        ],
        "tea_coffee": [
            "Traditional Mysuru Filter Coffee",
        ],
    },
}


def extract_food_preference(msg_lower: str) -> Optional[str]:
    """Detects specific dietary or culinary preference from the user's message."""
    if any(k in msg_lower for k in ["chicken", "murgh", "poultry"]):
        return "chicken"
    if any(k in msg_lower for k in ["mutton", "gosht", "lamb", "meat", "beef"]):
        return "mutton"
    if any(k in msg_lower for k in ["seafood", "fish", "prawn", "prawns", "crab", "shrimp"]):
        return "seafood"
    if any(k in msg_lower for k in ["vegetarian", "veg", "paneer", "vegan"]) and "non-veg" not in msg_lower and "non veg" not in msg_lower:
        return "vegetarian"
    if any(k in msg_lower for k in ["dessert", "desserts", "sweet", "sweets", "mithai", "halwa", "pastry", "ice cream"]):
        return "dessert"
    if any(k in msg_lower for k in ["tea", "chai", "coffee", "filter coffee"]):
        return "tea_coffee"
    if any(k in msg_lower for k in ["breakfast", "tiffin", "dosa", "idli"]):
        return "breakfast"
    return None


def extract_travel_intent_target(msg_lower: str) -> Optional[str]:
    """Detects if the user is expressing travel intent for a destination or trip."""
    if any(neg in msg_lower for neg in ["don't want to go", "dont want to go", "not want to go", "refuse to go", "hate going"]):
        return None

    patterns = [
        r"(?:i\s+)?(?:want\s+to|would\s+like\s+to|planning\s+to|thinking\s+of|can\s+we|let'?s)\s+(?:go\s+to|visit|travel\s+to|fly\s+to|head\s+to)\s+([a-zA-Z\s]+)",
        r"(?:plan|planning|create|start|organize)\s+(?:a\s+)?(?:new\s+)?trip\s+to\s+([a-zA-Z\s]+)",
        r"(?:trip|travel|vacation|holiday|flight)\s+to\s+([a-zA-Z\s]+)",
        r"^visit\s+([a-zA-Z\s]+)",
    ]
    for pat in patterns:
        m = re.search(pat, msg_lower)
        if m:
            target = m.group(1).strip()
            target = re.sub(r"[?!.,;]+$", "", target).strip()
            target_words = set(target.split())
            non_travel_words = {"school", "college", "work", "office", "class", "classes", "gym", "bed", "sleep", "home", "hospital", "doctor", "dentist", "court", "jail", "prison"}
            if target_words & non_travel_words:
                return None
            return target

    if any(k in msg_lower for k in ["want to travel", "want to take a trip", "plan another trip", "plan a new trip", "travel to a new place", "visit another country"]):
        return ""

    return None



def is_crisis_query(msg_lower: str) -> bool:
    """
    Critical safety detector for self-harm, suicide, or emotional crisis.
    Must intercept immediately before any conversational or travel planning logic.
    """
    crisis_patterns = [
        r"\b(?:kill|hurting|hurt|harm|cutting|cut|hang|poison|end)\s+(?:my\s*self|me)\b",
        r"\b(?:commit|attempt)\s+suicide\b",
        r"\b(?:suicidal|suicide)\b",
        r"\b(?:end(?:ing)?\s+(?:my\s+life|it\s+all))\b",
        r"\b(?:take\s+(?:my\s+own\s+life|my\s+life))\b",
        r"\b(?:want\s+to\s+die|wish\s+i\s+(?:was|were)\s+dead|better\s+off\s+dead)\b",
        r"\b(?:don'?t\s+want\s+to\s+live(?: anymore)?)\b",
        r"\b(?:slit\s+(?:my\s+)?wrists?)\b",
        r"\b(?:jump\s+off\s+(?:a\s+)?(?:bridge|cliff|building))\b",
        r"\b(?:overdose\s+and\s+die)\b",
        r"\b(?:self[-\s]harm)\b",
    ]
    return any(re.search(pat, msg_lower) for pat in crisis_patterns)


def answer_trip_question(
    trip_data: Dict[str, Any],
    message: str,
) -> Dict[str, Any]:
    """
    Trip-aware Copilot reasoning engine. Generates contextual answers based on
    destination, daily schedule, weather, budget, and traveler preferences.
    Distinguishes itinerary questions, modifications, greetings, and travel advice.
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

    day_sched = trip_data.get("day_schedule", {})
    all_places_list = [p.get("name", "") for d in day_sched.values() if isinstance(d, list) for p in d]
    places_str = ", ".join(all_places_list[:5]) if all_places_list else "top regional highlights"
    mutation_action = None

    # 0. CRITICAL SAFETY GUARDRAIL: SELF-HARM & SUICIDE CRISIS INTERVENTION
    if is_crisis_query(msg_lower):
        topic = "crisis_support"
        reply = (
            "If you are feeling overwhelmed, hopeless, or having thoughts of self-harm or suicide, "
            "please know that you are not alone and compassionate support is available right now. "
            "Your life has immense value, and there are trained professionals ready to listen and help without judgment.\n\n"
            "**Immediate Free & Confidential Helplines:**\n\n"
            "• **India (National):**\n"
            "  - **Tele-MANAS:** Call **14416** or **1800-891-4416** (24/7, Toll-Free, Govt of India)\n"
            "  - **KIRAN Mental Health Helpline:** Call **1800-599-0019** (24/7, Toll-Free)\n"
            "  - **Vandrevala Foundation:** Call or WhatsApp **+91 9999 666 555** (24/7, Free)\n\n"
            "• **United States & Canada:**\n"
            "  - **988 Suicide & Crisis Lifeline:** Call or text **988** (24/7, Free & Confidential)\n"
            "  - **Crisis Text Line:** Text **HOME** to **741741**\n\n"
            "• **International / Worldwide:**\n"
            "  - **Befrienders Worldwide:** [https://www.befrienders.org](https://www.befrienders.org)\n"
            "  - **Find A Helpline:** [https://findahelpline.com](https://findahelpline.com)\n\n"
            "If you are in immediate physical danger, please contact your local emergency services (like 112 in India, 911 in the US) "
            "or go to the nearest emergency hospital immediately. Please reach out to one of these resources or a trusted family member or friend right now."
        )
        suggestions = [
            "Call Tele-MANAS (14416)",
            "Call or text 988 Lifeline",
            "Reach out to a trusted loved one",
            "Find professional support",
        ]
        return {
            "reply": reply,
            "topic": topic,
            "suggested_actions": suggestions,
            "mutation_action": None,
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

    # 1. GREETINGS & CASUAL OPENINGS
    greeting_patterns = [r"^hi\b", r"^hello\b", r"^hey\b", r"^greetings\b", r"^good (morning|afternoon|evening)\b"]
    if any(re.search(pat, msg_lower) for pat in greeting_patterns) and len(msg_lower.split()) <= 4:
        topic = "greeting"
        reply = (
            f"Hello! I am your **TravelSync AI Assistant** for your trip to **{destination}**.\n\n"
            f"I can help you review which day is the busiest, replace attractions with cheaper options, "
            f"recommend local dishes, prepare packing checklists, or answer questions about your itinerary. "
            f"How can I help you today?"
        )
        suggestions = ["Which day is the busiest?", "Replace the most expensive attraction with a cheaper one", "What should I pack?", "Top local foods to try"]

    # 2. ITINERARY MODIFICATION (e.g. Replace most expensive attraction with cheaper one)
    elif any(k in msg_lower for k in ["replace", "swap", "substitute", "cheaper attraction", "cheaper one", "most expensive attraction"]):
        topic = "modification"
        all_candidate_places = trip_data.get("places", [])

        # Find all currently scheduled attractions with their days
        scheduled_items = []
        for d_str, places in day_sched.items():
            if isinstance(places, list):
                for idx, p in enumerate(places):
                    # Score cost: category weight or explicit price
                    cat = str(p.get("category", "")).lower()
                    cost_val = float(p.get("price") or p.get("cost") or p.get("estimated_cost") or 0.0)
                    if not cost_val:
                        # Category-based cost tier
                        if any(k in cat for k in ["luxury", "resort", "theme park", "adventure", "safari"]):
                            cost_val = 2500
                        elif any(k in cat for k in ["historic", "monument", "fort", "museum", "palace"]):
                            cost_val = 1000
                        elif any(k in cat for k in ["park", "garden", "lake", "viewpoint", "beach", "temple"]):
                            cost_val = 300
                        else:
                            cost_val = 700

                    scheduled_items.append({
                        "day": d_str,
                        "index": idx,
                        "name": p.get("name", "Attraction"),
                        "category": p.get("category", "General"),
                        "estimated_cost": cost_val,
                        "place_obj": p,
                    })

        if scheduled_items:
            # Sort by estimated cost descending
            scheduled_items.sort(key=lambda x: -x["estimated_cost"])
            target_to_replace = scheduled_items[0]

            # Find a lower-cost unscheduled alternative from places
            scheduled_names = {it["name"].lower() for it in scheduled_items}
            low_cost_alternatives = []
            for cp in all_candidate_places:
                cp_name = cp.get("name", "").strip()
                if not cp_name or cp_name.lower() in scheduled_names:
                    continue
                cp_cat = str(cp.get("category", "")).lower()
                cp_cost = float(cp.get("price") or cp.get("cost") or 0.0)
                if not cp_cost:
                    if any(k in cp_cat for k in ["park", "garden", "lake", "viewpoint", "beach", "temple", "nature"]):
                        cp_cost = 250
                    else:
                        cp_cost = 600

                if cp_cost < target_to_replace["estimated_cost"]:
                    low_cost_alternatives.append((cp_cost, cp))

            if low_cost_alternatives:
                low_cost_alternatives.sort(key=lambda x: x[0])
                chosen_cost, chosen_alt = low_cost_alternatives[0]

                # Apply modification to trip data copy
                import copy
                updated_sched = copy.deepcopy(day_sched)
                target_day = target_to_replace["day"]
                target_idx = target_to_replace["index"]

                new_place_entry = {
                    "name": chosen_alt.get("name"),
                    "category": chosen_alt.get("category", "Scenic Attraction"),
                    "lat": chosen_alt.get("lat"),
                    "lon": chosen_alt.get("lon"),
                    "distance_km": round(chosen_alt.get("distance_km", 2.0), 1),
                    "travel_from_previous_km": round(target_to_replace["place_obj"].get("travel_from_previous_km", 2.5), 1),
                    "travel_time_minutes": target_to_replace["place_obj"].get("travel_time_minutes", 20),
                    "time_window": target_to_replace["place_obj"].get("time_window", "11:00 AM"),
                    "timing_status": "Economical Alternative Pick",
                    "is_replacement": True,
                }
                updated_sched[target_day][target_idx] = new_place_entry

                # Clone trip and update budget & dashboard
                updated_trip = copy.deepcopy(trip_data)
                updated_trip["day_schedule"] = updated_sched

                from backend.services.planner.budget_tracker import calculate_budget
                from backend.services.planner.dashboard import build_dashboard
                sched_count = sum(len(p) for p in updated_sched.values() if isinstance(p, list))
                updated_trip["budget"] = calculate_budget(
                    travelers=travelers,
                    days=days,
                    travel_mode=mode,
                    hotels=trip_data.get("hotels", []),
                    places=updated_sched,
                    scheduled_activity_count=sched_count,
                    total_budget=budget.get("total_budget"),
                )
                updated_trip["dashboard"] = build_dashboard(updated_trip)

                cost_saved = int(target_to_replace["estimated_cost"] - chosen_cost)
                reply = (
                    f"✓ **Attraction Replacement Applied!**\n\n"
                    f"- **Replaced:** `{target_to_replace['name']}` (Day {target_day}, est. ₹{int(target_to_replace['estimated_cost']):,})\n"
                    f"- **New Alternative:** `{chosen_alt.get('name')}` ({chosen_alt.get('category', 'Attraction')}, est. ₹{int(chosen_cost):,})\n"
                    f"- **Estimated Savings:** **₹{cost_saved:,}**\n\n"
                    f"Your Day {target_day} schedule, trip budget, and analytics have been updated automatically."
                )
                mutation_action = {
                    "type": "replace_attraction",
                    "action": "replace_attraction",
                    "applied": True,
                    "target_day": target_day,
                    "old_attraction": target_to_replace["name"],
                    "new_attraction": chosen_alt.get("name"),
                    "savings_inr": cost_saved,
                    "updated_trip": updated_trip,
                }
                suggestions = ["Which day is the busiest now?", "Check budget overview", "Top local foods to try", "Optimal timing advice"]
            else:
                reply = (
                    f"I identified **{target_to_replace['name']}** on Day {target_to_replace['day']} as the highest-expense attraction. "
                    f"However, all other attractions in the destination candidate pool are already at similar or higher cost tiers. "
                    f"To reduce spend, consider reallocating surplus lodging budget or adjusting your transport mode."
                )
                suggestions = ["Check budget overview", "Which day is the busiest?", "Optimal timing advice"]
        else:
            reply = (
                "Unable to identify attractions to replace because the day schedule is currently empty. "
                "Add attractions to your itinerary first or run itinerary regeneration."
            )
            suggestions = ["What should I pack?", "Top local foods to try"]

    # 3. WEATHER & TEMPERATURE COMPARISONS (e.g. Which day is hottest and coldest?)
    elif any(k in msg_lower for k in ["hottest", "coldest", "temperature", "forecast", "hottest day", "coldest day"]) or ("which day" in msg_lower and any(w in msg_lower for w in ["hot", "cold", "warm", "temp", "weather"])):
        topic = "weather"
        if weather_list and isinstance(weather_list, list):
            valid_temps = []
            for idx, w in enumerate(weather_list):
                day_num = w.get("day", idx + 1)
                temp = w.get("temperature") or w.get("temp") or w.get("temp_max")
                cond = w.get("condition") or w.get("description") or "Clear"
                if temp is not None:
                    try:
                        valid_temps.append((int(day_num), float(temp), str(cond)))
                    except (ValueError, TypeError):
                        pass

            if valid_temps:
                valid_temps.sort(key=lambda x: x[1])
                coldest = valid_temps[0]
                hottest = valid_temps[-1]
                reply = (
                    f"**Weather & Temperature Forecast for {destination}:**\n\n"
                    f"• **Hottest Day:** Day {hottest[0]} with a forecast temperature of **{int(round(hottest[1]))}°C** ({hottest[2]}).\n"
                    f"• **Coldest Day:** Day {coldest[0]} with a forecast temperature of **{int(round(coldest[1]))}°C** ({coldest[2]}).\n\n"
                    f"*Travel Tip:* On Day {hottest[0]}, schedule strenuous outdoor walking before 10:30 AM or after 4:30 PM, "
                    f"and keep Day {coldest[0]} for full-day heritage trails."
                )
                suggestions = ["Today is so hot, what should I do?", "What should I pack?", "Which day is the busiest?", "Top local foods to try"]
            else:
                reply = (
                    f"Detailed daily temperature breakdown is unavailable for this date range in {destination}. "
                    f"The prevailing general condition is **{primary_weather}**. Plan for comfortable cotton clothing and stay hydrated!"
                )
                suggestions = ["Today is so hot, what should I do?", "What should I pack?", "Which day is the busiest?"]
        else:
            reply = (
                f"Live weather data is currently unavailable for {destination}. "
                f"We recommend checking regional conditions before departure and carrying versatile layers."
            )
            suggestions = ["What should I pack?", "Which day is the busiest?"]

    # 4. HEAT ADVICE & SUMMER SAFETY (e.g. Today is so hot, what should I do?)
    elif any(k in msg_lower for k in ["so hot", "too hot", "very hot", "extremely hot", "heat", "scorching", "beat the heat", "heat wave", "sunstroke", "avoid heat"]):
        topic = "weather_advice"
        reply = (
            f"**Beat-the-Heat Guide for {destination}:**\n\n"
            f"1. **Hydrate Continuously:** Carry an insulated flask with cool water, ORS/electrolytes, or fresh coconut water from roadside vendors.\n"
            f"2. **Midday Sun Avoidance (12:00 PM – 03:30 PM):** Retreat indoors during peak UV hours. Perfect time for air-conditioned museums, shaded cafes, or a rest break at your hotel.\n"
            f"3. **Pace Your Sightseeing:** Reschedule outdoor walks to the early morning (before 10:30 AM) or golden sunset hours (after 04:30 PM).\n"
            f"4. **Sun Protection:** Wear loose, light-colored breathable cottons, SPF 50+ sunscreen, UV sunglasses, and a wide-brim hat.\n"
            f"5. **Indoor Attractions:** Let me know if you would like me to swap any high-heat outdoor visits for nearby indoor cultural alternatives!"
        )
        suggestions = ["Which day is hottest and coldest?", "Top local foods to try", "Which day is the busiest?", "What should I pack?"]

    # 5. ITINERARY SCHEDULE QUESTIONS (e.g. Which day is the busiest?)
    elif any(k in msg_lower for k in ["busiest", "most busy", "crowded day", "heavy day", "dense day", "most stops", "packed day", "day schedule", "what is planned"]) or ("which day" in msg_lower and any(w in msg_lower for w in ["busiest", "busy", "crowded", "heavy", "dense", "packed", "stops"])):
        topic = "itinerary"
        if day_sched and isinstance(day_sched, dict):
            day_metrics = []
            for d_str, places in sorted(day_sched.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 99):
                p_list = places if isinstance(places, list) else []
                stop_count = len(p_list)
                d_dist = sum(float(p.get("travel_from_previous_km", 0) or 0) for p in p_list)
                d_mins = sum(int(p.get("travel_time_minutes", 15) or 15) for p in p_list)
                names = [p.get("name", "Stop") for p in p_list]
                day_metrics.append({
                    "day": d_str,
                    "count": stop_count,
                    "distance_km": round(d_dist, 1),
                    "transit_mins": d_mins,
                    "names": names,
                })

            if day_metrics:
                # Find day with highest stop count, tie-breaker transit time
                day_metrics.sort(key=lambda x: (x["count"], x["transit_mins"]), reverse=True)
                busiest = day_metrics[0]

                other_summaries = [
                    f"Day {m['day']} has {m['count']} stop(s)"
                    for m in day_metrics if m['day'] != busiest['day']
                ]
                others_text = f" (In comparison, {', '.join(other_summaries)})" if other_summaries else ""

                stop_names_bullet = "\n".join([f"  • {n}" for n in busiest["names"]]) if busiest["names"] else "  • No named stops recorded"

                reply = (
                    f"**Day {busiest['day']}** is the busiest day of your itinerary with **{busiest['count']} scheduled stops** "
                    f"and approximately ~{busiest['transit_mins']} minutes of transit ({busiest['distance_km']} km){others_text}.\n\n"
                    f"**Stops on Day {busiest['day']}:**\n"
                    f"{stop_names_bullet}\n\n"
                    f"*Pacing Recommendation:* Since Day {busiest['day']} is packed, plan a midday rest pause between 01:30 PM and 03:00 PM "
                    f"to keep energy levels fresh for evening sightseeing."
                )
                suggestions = ["Replace the most expensive attraction with a cheaper one", "What should I pack?", "Top local foods to try", "Optimal timing advice"]
            else:
                reply = "Your day schedule currently has no attractions recorded to evaluate daily density."
                suggestions = ["What should I pack?", "Top local foods to try"]
        else:
            reply = "Detailed daily schedule data is currently unavailable for this trip, so daily density cannot be evaluated."
            suggestions = ["What should I pack?", "Top local foods to try"]

    # 6. PACKING ADVICE
    elif any(k in msg_lower for k in ["pack", "what to wear", "clothing", "luggage", "dress code", "bag"]):
        topic = "packing"
        rain_likely = any("rain" in str(w.get("condition", "")).lower() for w in weather_list)
        is_warm = any(w.get("temperature", 25) > 28 for w in weather_list)

        items = [
            "Comfortable walking shoes / sneakers with grip for sightseeing and monument walks.",
            "Breathable lightweight cotton clothing suited for daytime outings.",
            "Modest attire (covering shoulders and knees) for temple or heritage monument entry.",
            "Power bank, universal charging adapter, and camera gear.",
            "Personal toiletries, reusable water bottle, and a compact daypack.",
        ]
        if rain_likely:
            items.insert(0, "Compact windproof umbrella and lightweight waterproof jacket or poncho.")
            items.append("Waterproof phone pouch and quick-dry footwear.")
        if is_warm:
            items.insert(1, "Sun protection essentials: SPF 50+ sunscreen, UV sunglasses, and a wide-brim hat.")

        history = trip_data.get("assistant_history", [])
        is_repeat = sum(1 for h in history if "pack" in str(h.get("text", "")).lower()) > 1
        prefix = "Here is your updated packing reminder" if is_repeat else "Here is your personalized packing checklist"

        reply = (
            f"{prefix} for **{destination}** ({days} days, {t_count} traveler(s)):\n\n"
            + "\n".join([f"- **{it}**" for it in items])
            + f"\n\n*Forecast Note:* Weather expects **{primary_weather}**. Traveling by **{mode.upper()}**, so keep essentials in an easily accessible cabin bag!"
        )
        suggestions = ["Which day is the busiest?", "Top local foods to try", "Safety and cultural etiquette", "Trip budget overview"]

    # 7. LOCAL FOOD & DINING GUIDE (e.g. I want to eat, chicken requests)
    elif any(k in msg_lower for k in ["food", "eat", "hungry", "dish", "dishes", "restaurant", "restaurants", "cuisine", "taste", "dining", "breakfast", "dinner", "lunch", "meal", "snack"]) or extract_food_preference(msg_lower) is not None:
        topic = "food"
        pref = extract_food_preference(msg_lower)
        matched_city = None
        for k in LOCAL_FOOD_PREFERENCES.keys():
            if k in dest_key or k in destination.lower() or dest_key in k:
                matched_city = k
                break

        dishes = []
        if pref and matched_city and pref in LOCAL_FOOD_PREFERENCES[matched_city]:
            dishes = LOCAL_FOOD_PREFERENCES[matched_city][pref]
        elif pref:
            if pref == "chicken":
                dishes = [
                    f"{destination.title()} Style Chicken Dum Biryani or Pulao",
                    f"Spiced Crispy Chicken Appetizer ({destination.title()} Style)",
                    f"Slow-Cooked Royal Chicken Curry / Rich Gravy",
                    f"Flame-Grilled Chicken Kebabs & Local Flatbreads",
                ]
            elif pref == "mutton":
                dishes = [
                    f"Signature {destination.title()} Mutton Biryani / Curry",
                    f"Slow-Simmered Meat Stew with Fragrant Spices",
                    f"Pan-Seared Spiced Mutton Kebabs",
                ]
            elif pref == "vegetarian":
                dishes = [
                    f"Authentic {destination.title()} Regional Dal / Lentil Preparation",
                    f"Paneer or Seasonal Vegetable Curry in Spiced Gravy",
                    f"Crispy Regional Street Snacks & Steamed Bread",
                ]
            elif pref == "seafood":
                dishes = [
                    f"Fresh Regional Spiced Catch-of-the-Day Fish Curry",
                    f"Crispy Rava or Pan-Fried Fish / Prawn Specialty",
                    f"Coastal Seafood Roast with Steamed Rice",
                ]
            elif pref == "dessert":
                dishes = [
                    f"Traditional {destination.title()} Milk & Cardamom Dessert",
                    f"Artisanal Syrupy Sweet or Warm Halwa",
                    f"Regional Kulfi or Sweet Pastry",
                ]
            elif pref == "tea_coffee":
                dishes = [
                    f"Freshly Brewed Specialty Regional Tea / Chai",
                    f"Traditional Aromatic Roasted Filter Coffee",
                ]
            else:
                dishes = [
                    f"Classic {destination.title()} Breakfast Platter",
                    f"Fresh Steamed Crepes / Savory Cakes with Chutneys",
                ]

        if not dishes:
            for k, items in LOCAL_FOOD_GUIDE.items():
                if k in dest_key or k in destination.lower() or dest_key in k:
                    dishes = items
                    break
            if not dishes:
                dishes = ["Signature regional curry with steamed bread", "Fresh street snacks at local markets", "Artisanal clay-pot dessert", "Specialty aromatic filter brew"]

        if pref == "chicken":
            header = f"Top **chicken specialties** to try in **{destination}**:"
            follow_up = "Do you have a preferred budget tier (e.g., casual street eats vs. sit-down dining) or a specific neighborhood/location in mind?"
        elif pref:
            header = f"Recommended **{pref} dishes** in **{destination}**:"
            follow_up = "Do you have a preferred budget tier or a specific neighborhood/location in mind?"
        else:
            header = f"Culinary highlights not to miss in **{destination}**:"
            follow_up = "Are you craving a specific cuisine preference (such as chicken, vegetarian, or street snacks), or looking for a specific budget tier?"

        disclaimer = (
            f"*(Note: These are general culinary specialty recommendations for {destination}. "
            f"Live verified restaurant location search is currently unavailable, but these dishes are widely served across prominent dining spots in the city.)*"
        )

        reply = (
            f"{header}\n\n"
            + "\n".join([f"{idx+1}. **{d}**" for idx, d in enumerate(dishes)])
            + f"\n\n{follow_up}\n\n"
            + f"{disclaimer}"
        )
        suggestions = ["Which day is the busiest?", "What should I pack?", "Trip budget overview", "Check weather advice"]

    # 6. TIMING & SUNSET SPOTS
    elif any(k in msg_lower for k in ["timing", "sunset", "sunrise", "best time", "hours", "when to visit"]):
        topic = "timing"
        first_place = all_places_list[0] if all_places_list else "the primary attraction"
        reply = (
            f"**Optimal Timing & Sunset Guide for {destination}:**\n\n"
            f"- **Morning Window (8:00 AM – 10:30 AM):** Best for outdoor heritage sites and temples before midday heat. Ideal for `{first_place}`.\n"
            f"- **Afternoon Window (12:30 PM – 3:30 PM):** Retreat into shaded cafes, museums, or rest breaks.\n"
            f"- **Golden Hour & Sunset (4:45 PM – 6:30 PM):** Unbeatable lighting for photography! Head to elevated viewpoints, waterfront promenades, or open hilltop fortresses.\n"
            f"- **Evening Pacing:** Unwind with dinner by 8:00 PM to keep your {days}-day rhythm fresh."
        )
        suggestions = ["Which day is the busiest?", "What local food should I try?", "Packing advice", "Trip budget overview"]

    # 7. SAFETY & LOCAL ETIQUETTE
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
        suggestions = ["Which day is the busiest?", "What should I pack?", "Top dishes to try", "Optimal timing advice"]

    # 8. BUDGET OVERVIEW & FINANCIAL QUESTIONS
    elif any(k in msg_lower for k in ["budget", "cost", "money", "expensive", "spend", "saving", "rupee", "inr", "financial"]):
        topic = "budget"
        categories = budget.get("categories", {})
        reply = (
            f"**Trip Financial Snapshot for {destination}:**\n\n"
            f"- **Total Budget:** ₹{budget.get('total_budget', 0):,}\n"
            f"- **Estimated Spend:** ₹{budget.get('estimated_cost', 0):,}\n"
            f"- **Remaining Balance:** ₹{remaining:,} (*Status: {budget_status}*)\n"
            f"- **Category Breakdown:**\n"
            f"  • Lodging: ₹{categories.get('hotel', 0):,}\n"
            f"  • Dining: ₹{categories.get('food', 0):,}\n"
            f"  • Transport: ₹{categories.get('transport', 0):,}\n"
            f"  • Activities: ₹{categories.get('activities', 0):,}\n"
            f"  • Emergency Buffer: ₹{categories.get('emergency', 0):,}\n\n"
            f"Tip: You can use the **Smart Budget Reallocation** card or ask me to 'replace the most expensive attraction' to save funds!"
        )
        suggestions = ["Replace the most expensive attraction with a cheaper one", "Which day is the busiest?", "What should I pack?", "Top local foods to try"]

    # 9. ASSISTANT CAPABILITIES EXPLORATION
    elif any(k in msg_lower for k in ["what can you do", "help me with what", "your features", "capabilities", "how can you help"]):
        topic = "capabilities"
        reply = (
            f"I am your dedicated **TravelSync AI Assistant** for your {days}-day trip to **{destination}**.\n\n"
            f"Here are key things I can do for you:\n"
            f"• **Itinerary Review:** Ask which day is busiest or evaluate schedule density.\n"
            f"• **Cost Optimization:** Ask to replace expensive attractions with cheaper options.\n"
            f"• **Weather & Safety:** Ask for temperature comparisons or heat-safety advice.\n"
            f"• **Local Dining:** Ask for authentic regional foods and restaurant recommendations.\n"
            f"• **Packing Checklists:** Ask what clothing and essentials to bring."
        )
        suggestions = ["Which day is the busiest?", "Replace the most expensive attraction with a cheaper one", "What should I pack?", "Top local foods to try"]

    # 10. TRAVEL INTENT & DESTINATION EXPLORATION (e.g. "i want to go to america", "plan a trip to New York")
    elif (travel_target := extract_travel_intent_target(msg_lower)) is not None:
        topic = "travel_intent"
        t_clean = travel_target.strip().lower()
        is_us = any(u in t_clean for u in ["america", "united states", "usa", "u.s.", "u.s"]) or t_clean == "us"

        if is_us:
            reply = (
                f"It sounds like you're expressing travel intent for the **United States**! 🇺🇸\n\n"
                f"Because the US covers vast and distinct regions:\n"
                f"- **East Coast:** Historic landmarks, world-class museums, and urban energy (e.g., New York City, Washington D.C., Boston).\n"
                f"- **West Coast:** Coastal highways, national parks, and iconic cities (e.g., California, San Francisco, Los Angeles, Seattle).\n"
                f"- **South & Sun Belt:** Warm weather, beaches, music culture, and theme parks (e.g., Florida, Orlando, Miami, Texas).\n\n"
                f"Which specific US city or region do you want to visit, and would you like help planning a full day-by-day itinerary or budget estimate for that trip?\n\n"
                f"*(Note: Your current **{destination}** itinerary remains completely saved and intact. We can explore new destinations here or return to your active {destination} schedule anytime!)*"
            )
            suggestions = [
                "Plan a trip to New York",
                "Plan a trip to California",
                f"Return to current {destination} trip",
                "Which day is the busiest?",
            ]
        elif travel_target:
            dest_title = travel_target.strip().title()
            reply = (
                f"Planning a trip to **{dest_title}** sounds exciting!\n\n"
                f"I can help you put together a custom travel plan for **{dest_title}**, including top attractions, "
                f"suggested pacing, and budget estimates. How many days are you planning to visit, and who will be traveling with you?\n\n"
                f"*(Note: Your current **{destination}** trip details remain completely saved and intact. You can explore new trip plans freely without affecting your existing trip!)*"
            )
            suggestions = [
                f"Plan a 3-day trip to {dest_title}",
                f"Budget estimate for {dest_title}",
                f"Return to current {destination} trip",
                "Which day is the busiest?",
            ]
        else:
            reply = (
                f"Where in the world are you thinking of traveling next? "
                f"Whether it's a coastal beach getaway, an active nature tour, or a vibrant city break, "
                f"I can help you structure an itinerary, plan daily stops, and estimate budgets.\n\n"
                f"*(Note: Your current **{destination}** itinerary remains completely saved and active.)*"
            )
            suggestions = [
                "Plan a trip to New York",
                f"Return to current {destination} trip",
                "Which day is the busiest?",
                "What should I pack?",
            ]

    # 11. UNRELATED / EVERYDAY DILEMMAS & OUT-OF-DOMAIN FALLBACK
    else:
        topic = "everyday_advice"
        suggestions = ["Which day is the busiest?", "What should I pack?", "Top local foods to try", "Check trip budget"]

        # 1. Attempt Gemini dynamic generation for intelligent context-aware reply
        gemini_reply = None
        try:
            gemini_prompt = (
                f"You are TravelSync AI, an intelligent, empathetic travel assistant helping a traveler for their trip to {destination}.\n"
                f"The user asked an everyday or non-travel question: \"{message}\".\n\n"
                f"Provide a friendly, safe, helpful response in 2 to 3 sentences:\n"
                f"1. Acknowledge and offer a short, sensible, constructive perspective on their everyday dilemma or question.\n"
                f"2. Politely mention that your primary expertise is helping them plan and enjoy their trip to {destination}.\n"
                f"Return as valid JSON: {{\"reply\": \"<your response>\"}}"
            )
            res = generate(gemini_prompt)
            if isinstance(res, dict) and res.get("reply"):
                gemini_reply = str(res["reply"]).strip()
        except Exception:
            gemini_reply = None

        if gemini_reply:
            reply = gemini_reply
        else:
            # 2. Robust, safe, empathetic topic-aware fallbacks
            # A. School, classes, homework, studies, exams
            if any(k in msg_lower for k in ["school", "homework", "exam", "exams", "class", "classes", "study", "studying", "college", "teacher", "assignment", "test"]):
                reply = (
                    "It's completely normal to feel unmotivated or hesitant about school or classes from time to time. "
                    "If you're feeling overwhelmed or exhausted, try taking a step back: get a restful night's sleep, "
                    "break down what's ahead into one manageable step at a time, or talk openly with a parent, trusted friend, or teacher. "
                    f"While my main focus is helping you plan and navigate your upcoming trip to **{destination}**, "
                    "taking care of your well-being comes first! Whenever you're ready to take a breather and look forward to your travel plans, I'm here."
                )
            # B. Work, jobs, career, office, boss
            elif any(k in msg_lower for k in ["work", "job", "office", "boss", "career", "shift", "colleague", "meeting"]):
                reply = (
                    "Work fatigue and everyday pressures can definitely weigh on you. "
                    "Make sure to take regular short breaks, stay hydrated, and set healthy boundaries where possible. "
                    f"As your **TravelSync AI Assistant**, my expertise is centered around your journey to **{destination}**. "
                    "Whenever you'd like to take a break from work thoughts and explore sights or dining for your vacation, let me know!"
                )
            # C. Boredom, tiredness, stress, emotional low
            elif any(k in msg_lower for k in ["bored", "tired", "sad", "lazy", "stressed", "anxious", "exhausted", "lonely", "sleepy", "burnout"]):
                reply = (
                    "We all have moments when our energy or spirits are running low. Be gentle with yourself today: "
                    "take a relaxing pause, listen to some music, or step outside for a little fresh air. "
                    f"While my specialty is as your **TravelSync AI Assistant** for **{destination}**, "
                    "I hope your day feels lighter soon! I'm always here if you want a fun distraction exploring your travel itinerary."
                )
            # D. Other everyday topics / non-travel tasks
            else:
                reply = (
                    f"That sounds like an everyday question outside my usual travel specialty! While my primary expertise is being your dedicated **TravelSync AI Assistant** "
                    f"for your trip to **{destination}** (guiding your itinerary schedule, packing, budget, and local food), "
                    "I hope things go smoothly for you. "
                    "Whenever you have questions about your travel days, places to visit, or local recommendations, I'm right here!"
                )

    return {
        "reply": reply,
        "topic": topic,
        "suggested_actions": suggestions,
        "mutation_action": mutation_action,
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
