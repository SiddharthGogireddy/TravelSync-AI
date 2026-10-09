import re


def parse_prompt(prompt: str):
    text = prompt.lower().strip()
    changes = {}

    # -------------------------
    # 1. BUDGET
    # -------------------------
    budget = re.search(
        r"(?:budget|under|below|within|maximum|max|limit|to)\D*₹?\s*(\d[\d,]*)",
        text,
        re.IGNORECASE,
    )

    if budget:
        changes["budget"] = int(
            budget.group(1).replace(",", "")
        )

    # -------------------------
    # 2. REGENERATE DAY / PREFERRED INTERESTS
    # -------------------------
    regenerate = re.search(
        r"(?:regenerate|redo|replan|rebuild)"
        r".*?"
        r"(?:day\s*)?(\d+)",
        text,
        re.IGNORECASE,
    )

    # Support: "Make day 2 more about food and history" or "Make Day 2 more focused on nature"
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

    # Helper to clean place string
    def clean_place_name(p: str) -> str:
        p = re.sub(
            r"\s+(?:from|to|in)\s+(?:my|the|our)?\s*trip\b",
            "",
            p,
            flags=re.IGNORECASE,
        )
        p = re.sub(
            r"\s+(?:please|thanks)$",
            "",
            p,
            flags=re.IGNORECASE,
        )
        return p.strip()

    # -------------------------
    # 3. COMBINED: REPLACE X WITH Y / SWAP X FOR Y
    # -------------------------
    m_replace = re.search(
        r"(?:replace|swap|substitute)\s+(?:the\s+)?(.+?)\s+(?:with|for|by)\s+(?:the\s+)?(.+?)$",
        text,
        re.IGNORECASE,
    )
    if m_replace:
        rem_p = clean_place_name(m_replace.group(1))
        add_p = clean_place_name(m_replace.group(2))
        if rem_p:
            changes["remove_place"] = rem_p
        if add_p:
            changes["add_place"] = add_p
        return changes

    # -------------------------
    # 4. COMBINED: REMOVE X AND ADD Y
    # -------------------------
    m_rem_add = re.search(
        r"(?:remove|delete|exclude)\s+(?:the\s+)?(.+?)\s+and\s+(?:add|include|visit)\s+(?:the\s+)?(.+?)$",
        text,
        re.IGNORECASE,
    )
    if m_rem_add:
        rem_p = clean_place_name(m_rem_add.group(1))
        add_p = clean_place_name(m_rem_add.group(2))
        if rem_p:
            changes["remove_place"] = rem_p
        if add_p:
            changes["add_place"] = add_p
        return changes

    # -------------------------
    # 5. COMBINED: ADD Y AND REMOVE X
    # -------------------------
    m_add_rem = re.search(
        r"(?:add|include|visit)\s+(?:the\s+)?(.+?)\s+and\s+(?:remove|delete|exclude)\s+(?:the\s+)?(.+?)$",
        text,
        re.IGNORECASE,
    )
    if m_add_rem:
        add_p = clean_place_name(m_add_rem.group(1))
        rem_p = clean_place_name(m_add_rem.group(2))
        if add_p:
            changes["add_place"] = add_p
        if rem_p:
            changes["remove_place"] = rem_p
        return changes

    # -------------------------
    # 6. INDEPENDENT REMOVE
    # -------------------------
    m_rem = re.search(
        r"(?:remove|delete|exclude)\s+(?:the\s+)?(.+?)(?:\s+from\s+(?:my|the|our)?\s*trip\b|$)",
        text,
        re.IGNORECASE,
    )
    if m_rem:
        rem_p = clean_place_name(m_rem.group(1))
        if rem_p:
            changes["remove_place"] = rem_p

    # -------------------------
    # 7. INDEPENDENT ADD
    # -------------------------
    m_add = re.search(
        r"(?:add|include|visit)\s+(?:the\s+)?(.+?)(?:\s+(?:to|in)\s+(?:my|the|our)?\s*trip\b|$)",
        text,
        re.IGNORECASE,
    )
    if m_add:
        add_p = clean_place_name(m_add.group(1))
        if add_p:
            changes["add_place"] = add_p

    return changes