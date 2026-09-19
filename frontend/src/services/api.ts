import type { TripRequest } from "../types/trip";
import type { TripResponse } from "../types/api";

// Base API URL for the frontend service layer.
// Falls back to a local development server if no Vite env URL is configured.
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function generateTrip(
    data: TripRequest
): Promise<TripResponse> {
    const res = await fetch(`${API}/planner/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });

    const result = await res.json();

    

    return result;
}
export async function updateTrip(
    tripId: string,
    prompt: string
): Promise<TripResponse> {
    const res = await fetch(`${API}/trip/${tripId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            prompt,
        }),
    });

    if (!res.ok) {
        const error = await res.text();
        throw new Error(error || "Failed to update trip");
    }

    const result = await res.json();

    return result;
}