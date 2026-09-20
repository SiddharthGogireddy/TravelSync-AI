import re


def parse_prompt(prompt: str):
    text = prompt.lower().strip()
    changes = {}

    # -------------------------
    # BUDGET
    # -------------------------
    budget = re.search(
        r"(?:budget|under|below|within|maximum|max|limit)"
        r"\D*₹?\s*(\d[\d,]*)",
        text,
        re.IGNORECASE,
    )

    if budget:
        changes["budget"] = int(
            budget.group(1).replace(",", "")
        )

    # -------------------------
    # REGENERATE DAY
    # -------------------------
    regenerate = re.search(
        r"(?:regenerate|redo|replan|rebuild)"
        r".*?"
        r"(?:day\s*)?(\d+)",
        text,
        re.IGNORECASE,
    )

    # Also support:
    # "Make day 2 more about food and history"
    make_day = re.search(
        r"(?:make|change|adjust|plan|replan)"
        r".*?"
        r"day\s*(\d+)",
        text,
        re.IGNORECASE,
    )

    day_match = regenerate or make_day

    if day_match:
        changes["regenerate_day"] = int(
            day_match.group(1)
        )

        preferred_interests = []

        interest_patterns = {
            "Food": r"\bfood\b",
            "History": r"\bhistory\b",
            "Culture": r"\bculture\b",
            "Nature": r"\bnature\b",
            "Adventure": r"\badventure\b",
            "Beaches": r"\bbeaches?\b",
            "Shopping": r"\bshopping\b",
            "Religion": r"\breligion\b",
        }

        for interest, pattern in interest_patterns.items():
            if re.search(pattern, text):
                preferred_interests.append(interest)

        if preferred_interests:
            changes["preferred_interests"] = preferred_interests

    # -------------------------
    # ADD PLACE
    # -------------------------
    add_match = re.search(
        r"(?:add|include|visit)\s+"
        r"(?:the\s+)?(.+?)(?:\s+to\s+(?:my\s+)?trip|\s+in\s+my\s+trip)?$",
        text,
        re.IGNORECASE,
    )

    if add_match:
        place = add_match.group(1).strip()

        # Remove common trailing words
        place = re.sub(
            r"\s+(?:please|thanks)$",
            "",
            place,
            flags=re.IGNORECASE,
        )

        if place:
            changes["add_place"] = place

    # -------------------------
    # REMOVE PLACE
    # -------------------------
    remove_match = re.search(
        r"(?:remove|delete|exclude)"
        r"\s+(?:the\s+)?(.+?)"
        r"(?:\s+from\s+(?:my\s+)?trip)?$",
        text,
        re.IGNORECASE,
    )

    if remove_match:
        place = remove_match.group(1).strip()

        place = re.sub(
            r"\s+(?:please|thanks)$",
            "",
            place,
            flags=re.IGNORECASE,
        )

        if place:
            changes["remove_place"] = place

    return changes