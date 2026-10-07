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
export async function getTrip(
    tripId: string
): Promise<TripResponse> {
    const res = await fetch(`${API}/trip/${tripId}`);

    if (!res.ok) {
        const error = await res.text();
        throw new Error(
            error || "Failed to load trip"
        );
    }

    const result = await res.json();

    return result;
}
export async function checkFavorite(
    tripId: string
): Promise<boolean> {
    const res = await fetch(
        `${API}/trip/${tripId}/favorite`
    );

    if (!res.ok) {
        throw new Error("Failed to check favorite");
    }

    const result = await res.json();

    return result.favorite;
}

export async function favoriteTrip(
    tripId: string
): Promise<void> {
    const res = await fetch(
        `${API}/trip/${tripId}/favorite`,
        {
            method: "POST",
        }
    );

    if (!res.ok) {
        throw new Error("Failed to favorite trip");
    }
}

export async function unfavoriteTrip(
    tripId: string
): Promise<void> {
    const res = await fetch(
        `${API}/trip/${tripId}/favorite`,
        {
            method: "DELETE",
        }
    );

    if (!res.ok) {
        throw new Error("Failed to unfavorite trip");
    }
}
export async function getTripNotes(
  tripId: string
): Promise<string[]> {
  const res = await fetch(
    `${API}/trip/${tripId}/notes`
  );

  if (!res.ok) {
    throw new Error("Failed to load notes");
  }

  const result = await res.json();

  return result.notes;
}


export async function addTripNote(
  tripId: string,
  note: string
): Promise<string[]> {
  const res = await fetch(
    `${API}/trip/${tripId}/notes?note=${encodeURIComponent(note)}`,
    {
      method: "POST",
    }
  );

  if (!res.ok) {
    throw new Error("Failed to add note");
  }

  const result = await res.json();

  return result.notes;
}


export async function deleteTripNote(
  tripId: string,
  noteIndex: number
): Promise<void> {
  const res = await fetch(
    `${API}/trip/${tripId}/notes/${noteIndex}`,
    {
      method: "DELETE",
    }
  );

  if (!res.ok) {
    throw new Error("Failed to delete note");
  }
}
export async function getTripRating(
  tripId: string
): Promise<{
  rating: number | null;
  feedback: string;
} | null> {
  const res = await fetch(
    `${API}/trip/${tripId}/rating`
  );

  if (!res.ok) {
    throw new Error("Failed to load rating");
  }

  const result = await res.json();

  return result.rating;
}


export async function rateTrip(
  tripId: string,
  rating: number,
  feedback: string
): Promise<void> {
  const params = new URLSearchParams({
    rating: rating.toString(),
    feedback,
  });

  const res = await fetch(
    `${API}/trip/${tripId}/rating?${params.toString()}`,
    {
      method: "POST",
    }
  );

  if (!res.ok) {
    throw new Error("Failed to save rating");
  }
}
export type TripHistoryItem = {
  id: string;
  data: {
    trip: {
      source?: string;
      destination?: string;
      days?: number;
      destination_location: {
        lat: number;
        lon: number;
      };
    };
  };
};

export async function getTripHistory(): Promise<TripHistoryItem[]> {
  const res = await fetch(`${API}/trip/history`);

  if (!res.ok) {
    throw new Error("Failed to load trip history");
  }

  const result = await res.json();

  return result.trips;
}

export function downloadTripPdf(tripId: string): void {
  window.open(
    `${API}/trip/${tripId}/pdf`,
    "_blank"
  );
}

export function exportTrip(tripId: string): void {
  window.open(
    `${API}/trip/${tripId}/export`,
    "_blank"
  );
}

export async function importTrip(
  tripData: unknown
): Promise<{
  trip_id: string;
  message: string;
  source: string;
  destination: string;
}> {
  const res = await fetch(`${API}/trip/import`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(tripData),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to import trip");
  }

  return await res.json();
}

export async function duplicateTrip(
  tripId: string
): Promise<{
  trip_id: string;
  original_trip_id: string;
  message: string;
}> {
  const res = await fetch(`${API}/trip/${tripId}/duplicate`, {
    method: "POST",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to duplicate trip");
  }

  return await res.json();
}

export interface TripComparisonMetrics {
  trip_id: string;
  source: string;
  destination: string;
  duration_days: number;
  travel_mode: string;
  total_distance_km: number;
  traveler_count: number;
  total_budget: number;
  estimated_cost: number;
  remaining_budget: number;
  budget_status: string;
  hotel_count: number;
  hotels: string[];
  attractions_count: number;
  weather_days_available: number;
  weather_summary: Array<{
    date: string;
    min_temp: number | string;
    max_temp: number | string;
  }>;
}

export interface TripComparisonResult {
  trip1: TripComparisonMetrics;
  trip2: TripComparisonMetrics;
  comparison: {
    cheaper_trip_id: string;
    cost_difference: number;
    shorter_duration_trip_id: string;
    longer_duration_trip_id: string;
    duration_difference_days: number;
    shorter_distance_trip_id: string;
    longer_distance_trip_id: string;
    distance_difference_km: number;
    higher_budget_trip_id: string;
    budget_difference: number;
    more_attractions_trip_id: string;
    attractions_difference: number;
  };
}

export async function compareTrips(
  trip1Id: string,
  trip2Id: string
): Promise<TripComparisonResult> {
  const params = new URLSearchParams({ trip1: trip1Id, trip2: trip2Id });
  const res = await fetch(`${API}/trip/compare?${params.toString()}`);

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to compare trips");
  }

  return await res.json();
}


