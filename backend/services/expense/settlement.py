def calculate_settlements(balances):

    creditors = []
    debtors = []

    for name, balance in balances.items():

        if balance > 0:
            creditors.append([name, balance])

        elif balance < 0:
            debtors.append([name, -balance])

    settlements = []

    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):

        debtor = debtors[i]
        creditor = creditors[j]

        amount = min(
            debtor[1],
            creditor[1],
        )

        settlements.append(
            {
                "from": debtor[0],
                "to": creditor[0],
                "amount": round(amount, 2),
            }
        )

        debtor[1] -= amount
        creditor[1] -= amount

        if debtor[1] == 0:
            i += 1

        if creditor[1] == 0:
            j += 1

    return settlements