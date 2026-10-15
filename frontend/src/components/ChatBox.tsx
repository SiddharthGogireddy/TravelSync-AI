import { useState } from "react";
import type { Expense } from "../types/expense";
import type { TripResponse } from "../types/api";
import { apiFetch } from "../services/api";

interface ChatContext {
    expenses: Expense[];
    trip: TripResponse["trip"];
}

export default function ChatBox({ context }: { context: ChatContext }) {
    const [msg, setMsg] = useState("");
    const [reply, setReply] = useState("");
    const [loading, setLoading] = useState(false);

    const send = async () => {
        if (!msg.trim()) return;
        setLoading(true);
        try {
            const data = await apiFetch<{ reply: string }>("/ai/chat", {
                method: "POST",
                body: JSON.stringify({
                    message: msg,
                    context,
                }),
            });
            setReply(data.reply);
        } catch {
            setReply("Failed to get response from AI assistant.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <input value={msg} onChange={e => setMsg(e.target.value)} disabled={loading} />
            <button onClick={send} disabled={loading}>{loading ? "Thinking..." : "Ask"}</button>
            <p>{reply}</p>
        </div>
    );
}