from typing import Dict, List, Optional, Any, Tuple


STRATEGY_TARGET_WEIGHTS = {
    "conservative": {
        "hotel": 0.38,
        "food": 0.25,
        "transport": 0.17,
        "activities": 0.10,
        "emergency": 0.10,
        "label": "Conservative & Balanced",
        "description": "Preserves a 10% emergency buffer while securing reliable lodging and steady meals.",
    },
    "experience": {
        "hotel": 0.30,
        "food": 0.28,
        "transport": 0.14,
        "activities": 0.22,
        "emergency": 0.06,
        "label": "Experience Maximizer",
        "description": "Funnels savings from lodging and transit into top attractions, tours, and culinary memories.",
    },
    "cost_saver": {
        "hotel": 0.32,
        "food": 0.22,
        "transport": 0.16,
        "activities": 0.12,
        "emergency": 0.18,
        "label": "Cost Saver / High Reserve",
        "description": "Minimizes non-essential overhead and retains an 18% reserve for shopping and unexpected savings.",
    },
}


def analyze_budget_reallocations(
    budget: Dict[str, Any],
    strategy: str = "conservative",
) -> Dict[str, Any]:
    """
    Analyzes current category allocations against dynamic strategic targets,
    identifying surpluses, deficits, and concrete trade-off recommendations.
    """
    strategy = str(strategy).lower().strip()
    if strategy not in STRATEGY_TARGET_WEIGHTS:
        strategy = "conservative"

    strategy_info = STRATEGY_TARGET_WEIGHTS[strategy]
    target_weights = {k: v for k, v in strategy_info.items() if isinstance(v, float)}

    categories = budget.get("categories", {})
    total_budget = budget.get("total_budget", 0)
    estimated_cost = budget.get("estimated_cost", 0)

    # Base budget to rebalance against
    base_amount = total_budget if total_budget > 0 else (estimated_cost if estimated_cost > 0 else 20000)

    category_analysis: Dict[str, Any] = {}
    total_proposed = 0
    trade_off_suggestions: List[Dict[str, Any]] = []

    for cat, weight in target_weights.items():
        curr_val = categories.get(cat, 0)
        proposed_val = round(base_amount * weight)
        total_proposed += proposed_val
        delta = proposed_val - curr_val

        curr_pct = round((curr_val / max(1, estimated_cost)) * 100) if estimated_cost > 0 else 0
        target_pct = round(weight * 100)

        status_text = "Balanced"
        if delta > 300:
            status_text = "Underfunded (Will receive funds)"
        elif delta < -300:
            status_text = "Surplus (Can be reallocated)"

        category_analysis[cat] = {
            "current_amount": curr_val,
            "proposed_amount": proposed_val,
            "delta_amount": delta,
            "current_percentage": curr_pct,
            "target_percentage": target_pct,
            "status": status_text,
        }

    # Generate actionable trade-off suggestions
    surplus_cats = [c for c, a in category_analysis.items() if a["delta_amount"] < -500]
    underfunded_cats = [c for c, a in category_analysis.items() if a["delta_amount"] > 500]

    for s_cat in surplus_cats:
        s_delta = abs(category_analysis[s_cat]["delta_amount"])
        for u_cat in underfunded_cats:
            u_delta = category_analysis[u_cat]["delta_amount"]
            transfer_amount = min(s_delta, u_delta)
            if transfer_amount >= 300:
                trade_off_suggestions.append({
                    "from_category": s_cat,
                    "to_category": u_cat,
                    "amount": round(transfer_amount),
                    "action": f"Reallocate INR {round(transfer_amount)} from {s_cat.title()} to {u_cat.title()}",
                    "impact": (
                        f"Free up INR {round(transfer_amount)} from {s_cat} surplus to strengthen your {u_cat} allocation "
                        f"for higher trip quality without increasing total spend."
                    ),
                })
                break

    # If no specific cross-category trade-offs, add general guideline
    if not trade_off_suggestions:
        if strategy == "experience":
            trade_off_suggestions.append({
                "from_category": "hotel",
                "to_category": "activities",
                "amount": round(base_amount * 0.05),
                "action": "Shift 5% from accommodation to priority sightseeing & culinary tours.",
                "impact": "Unlocks additional guided heritage tours and premium regional tasting dinners.",
            })
        elif strategy == "cost_saver":
            trade_off_suggestions.append({
                "from_category": "activities",
                "to_category": "emergency",
                "amount": round(base_amount * 0.06),
                "action": "Increase reserve buffer by 6% using free sights and community walks.",
                "impact": "Keeps total out-of-pocket expenses safely under your max spend target.",
            })
        else:
            trade_off_suggestions.append({
                "from_category": "transport",
                "to_category": "hotel",
                "amount": round(base_amount * 0.04),
                "action": "Optimize intra-city transport to upgrade hotel comfort tier.",
                "impact": "Allows selecting top-rated centrally located stays with complimentary breakfast.",
            })

    remaining_after_reallocation = max(0, total_budget - total_proposed)

    return {
        "active_strategy": strategy,
        "strategy_label": strategy_info["label"],
        "strategy_description": strategy_info["description"],
        "base_budget_amount": base_amount,
        "categories": category_analysis,
        "trade_off_suggestions": trade_off_suggestions,
        "available_strategies": [
            {"id": k, "label": v["label"], "description": v["description"]}
            for k, v in STRATEGY_TARGET_WEIGHTS.items()
        ],
        "projected_total": total_proposed,
        "projected_remaining": remaining_after_reallocation,
        "summary": (
            f"Optimized under '{strategy_info['label']}' strategy. "
            f"Allocates INR {category_analysis.get('hotel', {}).get('proposed_amount')} to Hotel, "
            f"INR {category_analysis.get('food', {}).get('proposed_amount')} to Dining, and "
            f"INR {category_analysis.get('activities', {}).get('proposed_amount')} to Activities."
        ),
    }


def apply_budget_reallocation(
    trip_data: Dict[str, Any],
    strategy: str = "conservative",
    custom_categories: Optional[Dict[str, int]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Applies the selected reallocation strategy or custom values to the trip budget.
    """
    current_budget = trip_data.get("budget", {})
    realloc_analysis = analyze_budget_reallocations(current_budget, strategy=strategy)

    new_categories: Dict[str, int] = {}
    if custom_categories and isinstance(custom_categories, dict):
        for k in ["hotel", "food", "transport", "activities", "emergency"]:
            if k in custom_categories and isinstance(custom_categories[k], (int, float)):
                new_categories[k] = round(custom_categories[k])
            else:
                new_categories[k] = realloc_analysis["categories"][k]["proposed_amount"]
    else:
        for k in ["hotel", "food", "transport", "activities", "emergency"]:
            new_categories[k] = realloc_analysis["categories"][k]["proposed_amount"]

    new_estimated_total = sum(new_categories.values())
    total_budget = current_budget.get("total_budget", new_estimated_total)
    remaining = total_budget - new_estimated_total

    if remaining > new_estimated_total * 0.20:
        new_status = "Under Budget"
    elif remaining >= 0:
        new_status = "Near Budget"
    else:
        new_status = "Over Budget"

    category_total = max(1, new_estimated_total)
    new_percentages = {
        k: round(v / category_total * 100)
        for k, v in new_categories.items()
    }

    current_budget["categories"] = new_categories
    current_budget["category_percentage"] = new_percentages
    current_budget["estimated_cost"] = new_estimated_total
    current_budget["remaining"] = remaining
    current_budget["status"] = new_status

    trip_data["budget"] = current_budget

    # Re-run analysis on updated budget
    updated_analysis = analyze_budget_reallocations(current_budget, strategy=strategy)
    trip_data["budget_reallocation"] = updated_analysis

    audit = {
        "success": True,
        "strategy": strategy,
        "new_estimated_cost": new_estimated_total,
        "new_remaining": remaining,
        "new_status": new_status,
        "summary": f"Smart budget reallocation successfully applied ({strategy.replace('_', ' ').title()}). Total: INR {new_estimated_total}.",
    }

    return trip_data, audit
