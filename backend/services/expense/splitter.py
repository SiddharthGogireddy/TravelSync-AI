def split_equally(expenses, travelers):
    paid = {
        traveler["name"]: 0
        for traveler in travelers
    }

    for expense in expenses:
        paid[expense["paid_by"]] += expense["amount"]

    total = sum(
        expense["amount"]
        for expense in expenses
    )

    share = total / len(travelers)

    balances = {}

    for traveler in travelers:
        balances[
            traveler["name"]
        ] = round(
            paid[traveler["name"]] - share,
            2,
        )

    return balances