import type { TripRequest } from "../types/trip";
import type { TripResponse } from "../types/api";
import { getAuthHeaders } from "./identity";

// Base API URL for the frontend service layer.
// Falls back to a local development server if no Vite env URL is configured.
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const API_BASE = API;

export async function generateTrip(
    data: TripRequest
): Promise<TripResponse> {
    const res = await fetch(`${API}/planner/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...getAuthHeaders(),
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
            ...getAuthHeaders(),
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
    const res = await fetch(`${API}/trip/${tripId}`, {
        headers: {
            ...getAuthHeaders(),
        },
    });

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
  created_at?: string;
  data: {
    trip?: {
      source?: string;
      destination?: string;
      days?: number;
      created_at?: string;
      destination_location?: {
        lat: number;
        lon: number;
      } | null;
      [key: string]: unknown;
    };
    dashboard?: unknown;
    summary?: unknown;
    created_at?: string;
    [key: string]: unknown;
  };
};

export async function getTripHistory(): Promise<TripHistoryItem[]> {
  const res = await fetch(`${API}/trip/history`);

  if (!res.ok) {
    throw new Error("Failed to load trip history");
  }

  const result = await res.json();

  return Array.isArray(result?.trips) ? result.trips : [];
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

export function exportTripCalendar(tripId: string): void {
  const link = document.createElement("a");
  link.href = `${API}/trip/${tripId}/export/calendar.ics`;
  link.setAttribute("download", "");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
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
  routeStop: any,
  allowRepeat: boolean = false
): Promise<{ success: boolean; trip: any; audit: any }> {
  const res = await fetch(`${API}/trip/${tripId}/add-route-stop`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ day, route_stop: routeStop, allow_repeat: allowRepeat }),
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
  trip?: any;
  audit?: any;
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

export interface AlternativeAttraction {
  name: string;
  category: string;
  description: string;
  score?: number;
  lat?: number;
  lon?: number;
  distance_km?: number;
  estimated_cost?: number;
}

export interface AttractionAlternativesResponse {
  success: boolean;
  destination: string;
  day: string;
  attraction_name: string;
  alternatives: AlternativeAttraction[];
  total_available: number;
}

export async function getAttractionAlternatives(
  tripId: string,
  day: string,
  attractionName: string
): Promise<AttractionAlternativesResponse> {
  const url = `${API}/trip/${tripId}/attraction-alternatives?day=${encodeURIComponent(day)}&attraction_name=${encodeURIComponent(attractionName)}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to load alternative attractions");
  }

  return await res.json();
}

export async function executeAttractionAction(
  tripId: string,
  day: string,
  attractionName: string,
  action: "remove" | "replace",
  replacementPlace?: Partial<AlternativeAttraction> | Record<string, any>
): Promise<{ success: boolean; trip: any; message: string }> {
  const res = await fetch(`${API}/trip/${tripId}/attraction-action`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      day,
      attraction_name: attractionName,
      action,
      replacement_place: replacementPlace || null,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || `Failed to ${action} attraction`);
  }

  return await res.json();
}

export interface PlaceDetail {
  name: string;
  place_type: string; // "attraction" | "hotel" | "dining" | "place"
  category?: string;
  description?: string;
  image_url?: string | null;
  image_source?: string | null;
  address?: string | null;
  lat?: number | null;
  lon?: number | null;
  map_url?: string | null;
  provider_rating?: number | null;
  provider_rating_source?: string | null;
  provider_reviews_count?: number | null;
  travelsync_match_score?: number | null;
  opening_hours?: {
    opens?: string;
    closes?: string;
    display?: string;
    closed_days?: string[];
    visit_duration_minutes?: number;
  } | null;
  estimated_visit_duration?: string | null;
  entry_fee?: string | null;
  best_time_to_visit?: string | null;
  website_url?: string | null;
  accessibility?: string | null;
  star_rating?: string | null;
  price_per_night?: string | null;
  amenities?: string[] | null;
  check_in_time?: string | null;
  check_out_time?: string | null;
  booking_url?: string | null;
  note?: string | null;
}

export async function getPlaceDetails(
  name: string,
  placeType: string = "attraction",
  category?: string,
  lat?: number,
  lon?: number
): Promise<{ success: boolean; details: PlaceDetail }> {
  const params = new URLSearchParams({
    name,
    place_type: placeType,
  });
  if (category) params.append("category", category);
  if (lat != null && !isNaN(lat)) params.append("lat", String(lat));
  if (lon != null && !isNaN(lon)) params.append("lon", String(lon));

  const res = await fetch(`${API}/places/details?${params.toString()}`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to load place details");
  }

  return await res.json();
}

export interface TripInvitation {
  invitation_id: string;
  trip_id?: string;
  token?: string;
  role: "viewer" | "editor";
  created_at: string;
  expires_at: string;
  status: "pending" | "accepted" | "declined" | "revoked" | "expired";
  accepted_by?: string | null;
  accepted_at?: string | null;
}

export interface InvitationPreview {
  valid: boolean;
  status: string;
  role: "viewer" | "editor";
  trip_id: string;
  destination: string;
  source: string;
  days: number;
  expires_at: string;
}

export async function createTripInvitation(
  tripId: string,
  role: "viewer" | "editor" = "viewer",
  expiresInDays: number = 7
): Promise<TripInvitation> {
  const res = await fetch(`${API}/trip/${tripId}/invitations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ role, expires_in_days: expiresInDays }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to create invitation");
  }

  return await res.json();
}

export async function getTripInvitations(tripId: string): Promise<TripInvitation[]> {
  const res = await fetch(`${API}/trip/${tripId}/invitations`, {
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to load invitations");
  }

  const data = await res.json();
  return data.invitations || [];
}

export async function revokeTripInvitation(tripId: string, invitationId: string): Promise<void> {
  const res = await fetch(`${API}/trip/${tripId}/invitations/${invitationId}`, {
    method: "DELETE",
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to revoke invitation");
  }
}

export async function previewInvitation(token: string): Promise<InvitationPreview> {
  const res = await fetch(`${API}/invitations/${token}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Invalid or expired invitation");
  }
  return await res.json();
}

export async function acceptInvitation(token: string): Promise<{ status: string; trip_id: string; role: string }> {
  const res = await fetch(`${API}/invitations/${token}/accept`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to accept invitation");
  }
  return await res.json();
}

export async function declineInvitation(token: string): Promise<{ status: string }> {
  const res = await fetch(`${API}/invitations/${token}/decline`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to decline invitation");
  }
  return await res.json();
}

export async function getLegacyTripsPreview(): Promise<any> {
  const res = await fetch(`${API}/trip/legacy/preview`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to fetch legacy trips preview");
  }
  return await res.json();
}

export async function createTripsBackup(): Promise<any> {
  const res = await fetch(`${API}/trip/legacy/backup`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to create trips backup");
  }
  return await res.json();
}

export async function claimLegacyTrip(tripId: string): Promise<any> {
  const res = await fetch(`${API}/trip/${tripId}/claim-legacy`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to claim legacy trip");
  }
  return await res.json();
}

export async function claimBatchLegacyTrips(tripIds?: string[]): Promise<any> {
  const res = await fetch(`${API}/trip/legacy/claim-batch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ trip_ids: tripIds }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to batch claim legacy trips");
  }
  return await res.json();
}

export async function getAuthUserInfo(): Promise<any> {
  const res = await fetch(`${API}/auth/me`, {
    headers: {
      ...getAuthHeaders(),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to fetch user auth info");
  }
  return await res.json();
}



