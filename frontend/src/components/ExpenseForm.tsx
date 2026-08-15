import { useState,useEffect } from "react";
import type { Expense } from "../types/expense";

interface Props {
    travelers: string[];
    onAdd: (expense: Expense) => void;
}

export default function ExpenseForm({ travelers, onAdd }: Props) {
    const [title, setTitle] = useState<string>("");
    const [amount, setAmount] = useState<number>(0);
    const [paidBy, setPaidBy] = useState<string>(travelers[0] || "");

    const [splitType, setSplitType] = useState<"equal" | "custom">("equal");
    const [participants, setParticipants] = useState<string[]>([]);
    const [customSplit, setCustomSplit] = useState<Record<string, number>>({});
    const [category, setCategory] = useState<string>("food");
    const handleParticipantToggle = (name: string) => {
        setParticipants((prev) =>
            prev.includes(name)
                ? prev.filter((p) => p !== name)
                : [...prev, name]
        );
    };

    const handleCustomChange = (name: string, value: number) => {
        setCustomSplit((prev) => ({
            ...prev,
            [name]: value,
        }));
    };

    const handleSubmit = () => {
        if (!title || amount <= 0 || participants.length === 0) return;

        onAdd({
            title,
            amount,
            paid_by: paidBy,
            split_type: splitType,
            participants,
            custom_split:
                splitType === "custom" ? customSplit : undefined,
            category,
        });

        // reset form 
        setTitle("");
        setAmount(0);
        setParticipants([]);
        setCustomSplit({});
        setSplitType("equal");
    };
    useEffect(() => {
    if (!title) return;

    const timer = setTimeout(async () => {
        const res = await fetch("/ai/categorize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title }),
        });

        const data = await res.json();
        setCategory(data.category);
    }, 500);

    return () => clearTimeout(timer);
}, [title]);
    return (
        <div className="card">
            <h3>Add Expense</h3>

            {/* Title */}
            <input
                type="text"
                placeholder="Expense title (e.g. Dinner)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
            />

            {/* Amount */}
            <input
                type="number"
                placeholder="Amount"
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
            />

            {/* Paid By */}
            <select
                value={paidBy}
                onChange={(e) => setPaidBy(e.target.value)}
            >
                {travelers.map((t) => (
                    <option key={t} value={t}>
                        {t}
                    </option>
                ))}
            </select>

            {/* Split Type */}
            <h4>Split Type</h4>
            <select
                value={splitType}
                onChange={(e) =>
                    setSplitType(e.target.value as "equal" | "custom")
                }
            >
                <option value="equal">Equal</option>
                <option value="custom">Custom</option>
            </select>

            {/* Participants */}
            <h4>Participants</h4>
            {travelers.map((name) => (
                <label key={name} style={{ display: "block" }}>
                    <input
                        type="checkbox"
                        checked={participants.includes(name)}
                        onChange={() => handleParticipantToggle(name)}
                    />
                    {name}
                </label>
            ))}
            <h4>Category</h4>
<select
    value={category}
    onChange={(e) => setCategory(e.target.value)}
>
    <option value="food">Food</option>
    <option value="travel">Travel</option>
    <option value="hotel">Hotel</option>
    <option value="activities">Activities</option>
    <option value="shopping">Shopping</option>
</select>
            {/* Custom Split */}
            {splitType === "custom" && (
                <div>
                    <h4>Custom Split</h4>
                    {participants.map((p) => (
                        <div key={p}>
                            {p}:
                            <input
                                type="number"
                                placeholder="Amount"
                                onChange={(e) =>
                                    handleCustomChange(
                                        p,
                                        Number(e.target.value)
                                    )
                                }
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* Submit */}
            <button onClick={handleSubmit}>Add Expense</button>
        </div>
    );
}