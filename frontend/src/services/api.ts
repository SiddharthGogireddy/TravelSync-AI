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

export interface TripInsightsMetrics {
  total_trip_cost: number;
  cost_per_traveler: number;
  cost_per_day: number;
  distance: number;
  attractions_per_day: number;
  average_distance_between_stops: number;
  traveler_count: number;
  budget_utilization_pct: number;
  hotel_count: number;
  total_attractions: number;
  days: number;
  planned_budget: number;
}

export interface DayBreakdown {
  day: string;
  attractions_count: number;
  travel_distance_km: number;
}

export interface TripInsightObservation {
  category: "budget" | "sightseeing" | "travel" | "route" | "group";
  type: "warning" | "success" | "info";
  title: string;
  description: string;
}

export interface TripInsightsResponse {
  trip_id: string;
  metrics: TripInsightsMetrics;
  day_by_day_breakdown: DayBreakdown[];
  observations: TripInsightObservation[];
}

export async function getTripInsights(
  tripId: string
): Promise<TripInsightsResponse> {
  const res = await fetch(`${API}/trip/${tripId}/insights`);

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to fetch trip insights");
  }

  return await res.json();
}

// -------------------------------------------------------------
// STEP 47: TRIP TEMPLATES SERVICE METHODS
// -------------------------------------------------------------

export async function getTemplates(): Promise<{ templates: import("../types/template").TripTemplate[] }> {
  const res = await fetch(`${API}/templates`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to load templates");
  }
  return await res.json();
}

export async function getTemplate(templateId: string): Promise<import("../types/template").TripTemplate> {
  const res = await fetch(`${API}/templates/${templateId}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to load template details");
  }
  return await res.json();
}

export async function saveTripAsTemplate(
  tripId: string,
  name?: string,
  description?: string,
  category?: string
): Promise<{ message: string; template_id: string; name: string; destination: string; duration_days: number }> {
  const res = await fetch(`${API}/trip/${tripId}/template`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: name || "",
      description: description || "",
      category: category || "General",
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to save trip as template");
  }

  return await res.json();
}

export async function createTripFromTemplate(
  templateId: string,
  overrides?: { source?: string; travel_mode?: string; budget?: number }
): Promise<{ message: string; trip_id: string; template_id: string; template_name: string }> {
  const res = await fetch(`${API}/templates/${templateId}/create-trip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(overrides || {}),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to create trip from template");
  }

  return await res.json();
}

export async function deleteTemplate(
  templateId: string
): Promise<{ message: string; template_id: string }> {
  const res = await fetch(`${API}/templates/${templateId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to delete template");
  }

  return await res.json();
}

export interface ReplanDayPayload {
  day: number;
  completed_attractions: string[];
  remaining_hours: number;
  current_location?: { lat: number; lon: number };
  current_location_name?: string;
  remaining_budget?: number;
}

export async function replanActiveDay(
  tripId: string,
  payload: ReplanDayPayload
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/replan-day`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to replan day");
  }

  return await res.json();
}

export async function addRouteStop(
  tripId: string,
  day: number,
  routeStop: any
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/add-route-stop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ day, route_stop: routeStop }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to add route stop");
  }

  return await res.json();
}

export async function switchTransportMode(
  tripId: string,
  travelMode: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/switch-transport`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ travel_mode: travelMode }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to switch transport mode");
  }

  return await res.json();
}

export async function reallocateTripBudget(
  tripId: string,
  strategy: string,
  customCategories?: Record<string, number>
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/reallocate-budget`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      strategy,
      custom_categories: customCategories,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to reallocate budget");
  }

  return await res.json();
}

export async function castGroupVote(
  tripId: string,
  travelerName: string,
  attractionName: string,
  vote: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/group-vote`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      traveler_name: travelerName,
      attraction_name: attractionName,
      vote,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to submit group vote");
  }

  return await res.json();
}

export async function resolveGroupConflicts(
  tripId: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/resolve-group-conflicts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to resolve group conflicts");
  }

  return await res.json();
}

export async function sendAssistantChatMessage(
  tripId: string,
  message: string
): Promise<{
  success: boolean;
  reply: string;
  topic: string;
  suggested_actions: string[];
  trip_highlights: any;
}> {
  const res = await fetch(`${API}/trip/${tripId}/assistant-chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to send chat message");
  }

  return await res.json();
}

export async function getTripOptimizationScore(
  tripId: string
): Promise<{ success: boolean; optimization_score: any }> {
  const res = await fetch(`${API}/trip/${tripId}/optimization-score`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to fetch trip optimization score");
  }

  return await res.json();
}

export async function optimizeTrip(
  tripId: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/optimize-trip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to optimize trip");
  }

  return await res.json();
}

