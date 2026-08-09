import type { Expense, Settlement } from "../types/expense";

export function calculateSettlement(expenses: Expense[]): Settlement[] {

    const balances: Record<string, number> = {};

    for (const exp of expenses) {
        const share = exp.amount / exp.splitBetween.length;

        for (const person of exp.splitBetween) {
            balances[person] = (balances[person] || 0) - share;
        }

        balances[exp.paidBy] += exp.amount;
    }

    const creditors: [string, number][] = [];
    const debtors: [string, number][] = [];

    for (const person in balances) {
        if (balances[person] > 0) creditors.push([person, balances[person]]);
        else if (balances[person] < 0) debtors.push([person, balances[person]]);
    }

    const settlements: Settlement[] = [];

    for (const [debtor, debt] of debtors) {
        let remainingDebt = -debt;

        for (const creditor of creditors) {
            if (remainingDebt === 0) break;

            const pay = Math.min(remainingDebt, creditor[1]);

            if (pay > 0) {
                settlements.push({
                    from: debtor,
                    to: creditor[0],
                    amount: Math.round(pay)
                });

                creditor[1] -= pay;
                remainingDebt -= pay;
            }
        }
    }

    return settlements;
}