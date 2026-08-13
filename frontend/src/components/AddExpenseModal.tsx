import { useState } from "react";

type Props = {
    onAdd: (
        title: string,
        amount: number,
        paidBy: string
    ) => Promise<void>;

    travelers: string[];
};

export default function AddExpenseModal({
    onAdd,
    travelers,
}: Props) {

    const [title, setTitle] = useState("");

    const [amount, setAmount] = useState(0);

    const [paidBy, setPaidBy] = useState("");

    return (
        <div
            style={{
                background: "white",
                padding: 20,
                borderRadius: 10,
                marginBottom: 20,
            }}
        >
            <h2>Add Expense</h2>

            <input
                placeholder="Title"
                value={title}
                onChange={(e) =>
                    setTitle(e.target.value)
                }
            />

            <br /><br />

            <input
                type="number"
                placeholder="Amount"
                value={amount}
                onChange={(e) =>
                    setAmount(
                        Number(e.target.value)
                    )
                }
            />

            <br /><br />

            <select
                value={paidBy}
                onChange={(e) =>
                    setPaidBy(e.target.value)
                }
            >
                <option value="">
                    Select Traveler
                </option>

                {travelers.map((traveler) => (
                    <option
                        key={traveler}
                        value={traveler}
                    >
                        {traveler}
                    </option>
                ))}

            </select>

            <br /><br />

            <button
                onClick={() =>
                    onAdd(
                        title,
                        amount,
                        paidBy
                    )
                }
            >
                Add Expense
            </button>

        </div>
    );
}