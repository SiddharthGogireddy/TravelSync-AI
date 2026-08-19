import re


def parse_prompt(prompt: str):

    text = prompt.lower()

    changes = {}

    budget = re.search(r"\d+", text)

    if "budget" in text and budget:

        changes["budget"] = int(
            budget.group()
        )

    if "add" in text:

        place = text.replace(
            "add",
            ""
        ).strip()

        changes["add_place"] = place

    if "remove" in text:

        place = text.replace(
            "remove",
            ""
        ).strip()

        changes["remove_place"] = place

    regenerate = re.search(
        r"day\s+(\d+)",
        text
    )

    if (
        "regenerate" in text
        and regenerate
    ):

        changes["regenerate_day"] = int(
            regenerate.group(1)
        )

    return changes

