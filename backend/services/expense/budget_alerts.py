def get_budget_alerts(budget_comparison):
    alerts = []

    for category, data in budget_comparison.items():
        planned = data["planned"]
        actual = data["actual"]
        remaining = data["remaining"]

        if planned <= 0:
            continue

        percentage_used = (actual / planned) * 100

        if percentage_used >= 100:
            alerts.append({
                "category": category,
                "status": "over_budget",
                "message": f"{category.title()} budget exceeded by ₹{abs(remaining):.2f}",
                "percentage_used": round(percentage_used, 2)
            })

        elif percentage_used >= 80:
            alerts.append({
                "category": category,
                "status": "warning",
                "message": f"{category.title()} budget is {round(percentage_used)}% used",
                "percentage_used": round(percentage_used, 2)
            })

    return alerts