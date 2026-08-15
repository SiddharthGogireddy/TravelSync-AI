import { useState } from "react";
import type { Expense } from "../types/expense";
import type { TripResponse } from "../types/api";

interface ChatContext {
    expenses: Expense[];
    trip: TripResponse["trip"];
}
export default function ChatBox({ context }: { context: ChatContext }) {
    const [msg, setMsg] = useState("");
    const [reply, setReply] = useState("");

    const send = async () => {
        const res = await fetch("/ai/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: msg,
                context,
            }),
        });

        const data = await res.json();
        setReply(data.reply);
    };

    return (
        <div>
            <input value={msg} onChange={e => setMsg(e.target.value)} />
            <button onClick={send}>Ask</button>
            <p>{reply}</p>
        </div>
    );
}