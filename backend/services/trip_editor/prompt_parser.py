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

    if regenerate:
        changes["regenerate_day"] = int(
            regenerate.group(1)
        )

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