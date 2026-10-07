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