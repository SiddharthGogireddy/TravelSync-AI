import type { TripRequest } from "../types/trip";
import type { TripApiResponse } from "../types/api";

// Base API URL for the frontend service layer.
// Falls back to a local development server if no Vite env URL is configured.
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function generateTrip(
    data: TripRequest
): Promise<TripApiResponse> {

    const res = await fetch(`${API}/planner`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    return await res.json();
}

