import type { TripRequest  } from "../types/trip";
const API = "http://127.0.0.1:8000";

export async function generateTrip(data: TripRequest) {

    const res = await fetch(`${API}/planner`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    return await res.json();
}