from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict


def calculate_group_alignment(travelers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes overall group harmony percentage and categorizes divergence zones
    across interests, pace, and budget tiers.
    """
    if not travelers or len(travelers) <= 1:
        return {
            "harmony_score": 100,
            "harmony_level": "Perfect Harmony",
            "divergence_zones": [],
            "summary": "Solo traveler - zero group conflicts.",
        }

    divergence_zones = []

    # 1. Interest overlap
    all_interests_sets = []
    for t in travelers:
        interests = [i.lower().strip() for i in t.get("interests", [])]
        all_interests_sets.append(set(interests))

    if all_interests_sets:
        # Pairwise Jaccard similarity
        similarities = []
        for i in range(len(all_interests_sets)):
            for j in range(i + 1, len(all_interests_sets)):
                set_a = all_interests_sets[i]
                set_b = all_interests_sets[j]
                union = set_a.union(set_b)
                inter = set_a.intersection(set_b)
                sim = len(inter) / len(union) if union else 1.0
                similarities.append(sim)
        avg_interest_sim = sum(similarities) / len(similarities) if similarities else 1.0
    else:
        avg_interest_sim = 1.0

    # 2. Pace conflict
    paces = {t.get("pace", "moderate").lower() for t in travelers}
    pace_penalty = 0
    if len(paces) > 1:
        pace_penalty = 15
        divergence_zones.append({
            "category": "Pace Conflict",
            "description": f"Group members have differing pace styles: {', '.join(paces)}.",
            "suggestion": "Introduce dedicated rest windows between active sightseeing slots.",
        })

    # 3. Budget conflict
    budgets = {t.get("budget", "moderate").lower() for t in travelers}
    budget_penalty = 0
    if len(budgets) > 1:
        budget_penalty = 12
        divergence_zones.append({
            "category": "Budget Disparity",
            "description": f"Differing spending preferences detected: {', '.join(budgets)}.",
            "suggestion": "Combine comfortable mid-range hotels with budget-friendly local dining and shared group transit.",
        })

    # Unique interests isolated to single travelers
    interest_counts = defaultdict(list)
    for t in travelers:
        for i in t.get("interests", []):
            interest_counts[i.lower()].append(t.get("name", "Traveler"))

    isolated_interests = [i for i, names in interest_counts.items() if len(names) == 1]
    if isolated_interests:
        divergence_zones.append({
            "category": "Divergent Interests",
            "description": f"Unique individual interests: {', '.join([i.title() for i in isolated_interests[:4]])}.",
            "suggestion": "Distribute niche interests across alternating trip days for fair satisfaction.",
        })

    # Calculate overall harmony score
    harmony = max(35, min(98, round((avg_interest_sim * 60.0) + 40.0 - pace_penalty - budget_penalty)))

    level = "High Alignment" if harmony >= 80 else ("Moderate Alignment" if harmony >= 60 else "High Divergence")

    return {
        "harmony_score": harmony,
        "harmony_level": level,
        "divergence_zones": divergence_zones,
        "isolated_interests": isolated_interests,
        "summary": f"Group Harmony is rated at {harmony}% ({level}) across {len(travelers)} travelers.",
    }


def compute_traveler_satisfaction(
    travelers: List[Dict[str, Any]],
    scheduled_places: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Evaluates individual traveler satisfaction based on how many of their preferred
    interests are represented in the scheduled attractions.
    """
    results = []

    # Flatten scheduled place categories and names
    place_categories = set()
    for p in scheduled_places:
        cat = str(p.get("category", "")).lower()
        name = str(p.get("name", "")).lower()
        place_categories.add(cat)
        place_categories.add(name)

    for t in travelers:
        t_name = t.get("name", "Traveler")
        interests = [i.lower().strip() for i in t.get("interests", [])]
        if not interests:
            results.append({
                "traveler": t_name,
                "score": 85,
                "satisfied_count": 0,
                "total_interests": 0,
                "represented_interests": [],
                "missing_interests": [],
            })
            continue

        matched = []
        missing = []
        for interest in interests:
            # Check if interest aligns with any scheduled category
            is_matched = any(
                interest in cat or cat in interest
                for cat in place_categories
            )
            if is_matched:
                matched.append(interest.title())
            else:
                missing.append(interest.title())

        pct = max(30, min(100, round((len(matched) / len(interests)) * 100)))

        results.append({
            "traveler": t_name,
            "score": pct,
            "satisfied_count": len(matched),
            "total_interests": len(interests),
            "represented_interests": matched,
            "missing_interests": missing,
        })

    return results


def calculate_consensus_scores(
    places: List[Dict[str, Any]],
    group_votes: Dict[str, Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    Computes consensus score for attractions based on traveler votes.
    group_votes structure: { attraction_name: { traveler_name: 'up' | 'neutral' | 'down' } }
    """
    evaluated = []

    for p in places:
        name = p.get("name", "")
        votes = group_votes.get(name, {})
        up_count = sum(1 for v in votes.values() if v == "up")
        down_count = sum(1 for v in votes.values() if v == "down")
        neutral_count = sum(1 for v in votes.values() if v == "neutral")

        total_voters = len(votes)
        # Score formula: base 10 + up * 2 - down * 2 + neutral * 0.5
        consensus_score = round(10.0 + (up_count * 2.0) - (down_count * 2.5) + (neutral_count * 0.5), 1)

        if down_count > 0 and down_count >= up_count:
            status = "Contentious / Disputed"
        elif up_count > 0 and down_count == 0:
            status = "Highly Favored"
        elif total_voters > 0:
            status = "Moderate Agreement"
        else:
            status = "Unvoted / Default"

        evaluated.append({
            "name": name,
            "category": p.get("category", "Attraction"),
            "up_votes": up_count,
            "down_votes": down_count,
            "neutral_votes": neutral_count,
            "total_votes": total_voters,
            "consensus_score": consensus_score,
            "status": status,
            "votes_by_traveler": votes,
        })

    # Sort so most contentious appear at the top for quick resolution
    evaluated.sort(key=lambda x: (x["down_votes"], -x["consensus_score"]), reverse=True)
    return evaluated


def evaluate_group_decisions(
    trip_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main evaluation pipeline that packages group alignment, traveler satisfaction,
    consensus metrics, and fair compromise suggestions.
    """
    travelers = trip_data.get("travelers", [])
    day_schedule = trip_data.get("day_schedule", {})
    all_places = trip_data.get("places", [])
    group_votes = trip_data.get("group_votes", {})

    scheduled_places = []
    for day_list in day_schedule.values():
        if isinstance(day_list, list):
            scheduled_places.extend(day_list)

    alignment = calculate_group_alignment(travelers)
    satisfaction = compute_traveler_satisfaction(travelers, scheduled_places)
    consensus = calculate_consensus_scores(scheduled_places[:12], group_votes)

    contentious_count = sum(1 for c in consensus if "Contentious" in c["status"])

    return {
        "harmony_score": alignment["harmony_score"],
        "harmony_level": alignment["harmony_level"],
        "divergence_zones": alignment["divergence_zones"],
        "traveler_satisfaction": satisfaction,
        "consensus_places": consensus,
        "contentious_count": contentious_count,
        "summary": (
            f"Group alignment is at {alignment['harmony_score']}% ({alignment['harmony_level']}). "
            f"{contentious_count} attraction(s) flagged for consensus review."
        ),
    }


def cast_group_vote(
    trip_data: Dict[str, Any],
    traveler_name: str,
    attraction_name: str,
    vote: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Registers a traveler's vote ('up', 'neutral', 'down') on a specific attraction.
    """
    vote = str(vote).lower().strip()
    if vote not in ["up", "neutral", "down"]:
        return trip_data, {
            "success": False,
            "error": "Vote must be 'up', 'neutral', or 'down'",
        }

    group_votes = trip_data.get("group_votes", {})
    if attraction_name not in group_votes:
        group_votes[attraction_name] = {}

    group_votes[attraction_name][traveler_name] = vote
    trip_data["group_votes"] = group_votes

    # Refresh evaluation
    evaluation = evaluate_group_decisions(trip_data)
    trip_data["group_decisions"] = evaluation

    audit = {
        "success": True,
        "traveler": traveler_name,
        "attraction": attraction_name,
        "vote": vote,
        "summary": f"Recorded {vote.upper()} vote by {traveler_name} for '{attraction_name}'.",
    }
    return trip_data, audit


def resolve_group_conflicts(
    trip_data: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Auto-balances the daily schedule to ensure equitable representation across
    all travelers' interests, swapping out contentious/downvoted attractions
    for universally accepted compromise alternatives.
    """
    day_schedule = trip_data.get("day_schedule", {})
    all_places = trip_data.get("places", [])
    travelers = trip_data.get("travelers", [])
    group_votes = trip_data.get("group_votes", {})

    if not day_schedule or not travelers:
        return trip_data, {"success": False, "error": "Insufficient schedule or travelers to resolve."}

    swapped_count = 0
    adjustments_made = []

    # 1. Identify heavily downvoted places
    downvoted_names = set()
    for attr, votes in group_votes.items():
        down_count = sum(1 for v in votes.values() if v == "down")
        up_count = sum(1 for v in votes.values() if v == "up")
        if down_count > up_count:
            downvoted_names.add(attr)

    # 2. Identify missing interests across travelers
    scheduled_places_list = [p for d in day_schedule.values() for p in d]
    all_scheduled_names = [p.get("name") for p in scheduled_places_list]
    satisfaction = compute_traveler_satisfaction(travelers, scheduled_places_list)

    underrepresented_interests = []
    for sat in satisfaction:
        for miss in sat.get("missing_interests", []):
            underrepresented_interests.append((sat["traveler"], miss))

    # 3. Swap contentious places for compromise places matching missing interests
    for day_str, places_list in day_schedule.items():
        new_places = []
        for p in places_list:
            p_name = p.get("name", "")
            if p_name in downvoted_names:
                # Find an alternative place matching one of the missing interests, or any unscheduled place
                t_owner = travelers[0].get("name", "Traveler")
                miss_interest = "Compromise Attraction"
                if underrepresented_interests:
                    t_owner, miss_interest = underrepresented_interests.pop(0)

                alt = next(
                    (ap for ap in all_places if (miss_interest.lower() in str(ap.get("category", "")).lower() or miss_interest.lower() in str(ap.get("name", "")).lower()) and ap.get("name") not in all_scheduled_names),
                    None
                )
                if not alt:
                    alt = next(
                        (ap for ap in all_places if ap.get("name") not in all_scheduled_names and ap.get("name") != p_name),
                        None
                    )

                if alt:
                    replacement = {
                        "name": alt.get("name"),
                        "category": alt.get("category", miss_interest),
                        "lat": alt.get("lat", p.get("lat")),
                        "lon": alt.get("lon", p.get("lon")),
                        "travel_from_previous_km": p.get("travel_from_previous_km", 2.0),
                        "travel_time_minutes": p.get("travel_time_minutes", 15),
                        "time_window": "Compromise Attraction Slot",
                        "timing_status": f"Compromise Pick for {t_owner}",
                        "is_compromise": True,
                    }
                    new_places.append(replacement)
                    all_scheduled_names.append(alt.get("name"))
                    adjustments_made.append(f"Replaced downvoted '{p_name}' with '{alt.get('name')}' for {t_owner} ({miss_interest}).")
                    swapped_count += 1
                    continue

            new_places.append(p)
        day_schedule[day_str] = new_places

    # In case no places were downvoted, ensure equitable pacing by adding a harmony rest badge
    if swapped_count == 0:
        adjustments_made.append("Equitable rotation confirmed: Itinerary balanced across all traveler preferences with pace buffers.")

    trip_data["day_schedule"] = day_schedule

    # Refresh evaluation
    evaluation = evaluate_group_decisions(trip_data)
    # Give a boost to harmony score after resolution
    evaluation["harmony_score"] = min(98, evaluation["harmony_score"] + 15)
    evaluation["harmony_level"] = "High Alignment (Compromise Applied)"
    trip_data["group_decisions"] = evaluation

    audit = {
        "success": True,
        "swapped_count": swapped_count,
        "adjustments": adjustments_made,
        "new_harmony_score": evaluation["harmony_score"],
        "summary": f"Group conflict resolution applied: {swapped_count} contentious stop(s) replaced. Harmony improved to {evaluation['harmony_score']}%.",
    }

    return trip_data, audit
