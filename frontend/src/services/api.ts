import type { TripRequest, SuggestDatesParams, SuggestDatesResponse } from "../types/trip";
import type { TripResponse } from "../types/api";
import { getAuthHeaders, ensureAuthSession, getAuthToken } from "./identity";

// Base API URL for the frontend service layer.
// Falls back to a local development server if no Vite env URL is configured.
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const API_BASE = API;

/**
 * Standardized API Error class for frontend error handling.
 */
export class ApiError extends Error {
  public status: number;
  public errorCode: string;
  public detail: any;
  public details?: any;
  public isNetworkError: boolean;
  public isAuthError: boolean;
  public isValidationError: boolean;
  public isServerError: boolean;

  constructor(
    message: string,
    options: {
      status?: number;
      errorCode?: string;
      detail?: any;
      details?: any;
      isNetworkError?: boolean;
    } = {}
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status ?? 0;
    this.errorCode =
      options.errorCode ??
      (options.isNetworkError
        ? "NETWORK_ERROR"
        : options.status
        ? `HTTP_${options.status}`
        : "UNKNOWN_ERROR");
    this.detail = options.detail;
    this.details = options.details;
    this.isNetworkError = !!options.isNetworkError || options.status === 0;
    this.isAuthError = options.status === 401 || options.status === 403;
    this.isValidationError = options.status === 422;
    this.isServerError = (options.status ?? 0) >= 500;
  }
}

// In-flight mutation tracking to prevent duplicate submissions
const activeMutations = new Set<string>();

export interface ApiFetchOptions extends RequestInit {
  retries?: number;
  retryDelayMs?: number;
  mutationKey?: string;
  preventDuplicate?: boolean;
  _isAuthRetry?: boolean;
}

/**
 * Parse an API error response safely without leaking malformed JSON or unhandled promises.
 */
export async function parseApiError(res: Response): Promise<ApiError> {
  const status = res.status;
  let data: any = null;
  let text = "";
  try {
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await res.json();
    } else {
      text = await res.text();
    }
  } catch {
    // ignore parse failure
  }

  const errorCode =
    data?.error_code ||
    (status === 400
      ? "BAD_REQUEST"
      : status === 401
      ? "UNAUTHORIZED"
      : status === 403
      ? "FORBIDDEN"
      : status === 404
      ? "NOT_FOUND"
      : status === 409
      ? "CONFLICT"
      : status === 413
      ? "PAYLOAD_TOO_LARGE"
      : status === 422
      ? "VALIDATION_ERROR"
      : status === 429
      ? "TOO_MANY_REQUESTS"
      : status >= 500
      ? "INTERNAL_SERVER_ERROR"
      : `HTTP_${status}`);

  let safeMessage = data?.message;
  if (!safeMessage || typeof safeMessage !== "string") {
    if (typeof data?.detail === "string" && data.detail.trim()) {
      safeMessage = data.detail;
    } else if (status === 400) {
      safeMessage = "The request was invalid. Please check your inputs.";
    } else if (status === 401) {
      safeMessage = "Your session has expired or authentication is missing. Please sign in.";
    } else if (status === 403) {
      safeMessage = "You do not have permission to perform this action.";
    } else if (status === 404) {
      safeMessage = "The requested resource could not be found.";
    } else if (status === 409) {
      safeMessage = "A conflicting resource update occurred. Please refresh and try again.";
    } else if (status === 422) {
      safeMessage = "Some submitted information is invalid. Please review required fields.";
    } else if (status === 429) {
      safeMessage = "Too many requests. Please slow down and try again shortly.";
    } else if (status >= 500) {
      safeMessage = "A server error occurred. Please try again later.";
    } else {
      safeMessage = text || `Request failed with status ${status}`;
    }
  }

  return new ApiError(safeMessage, {
    status,
    errorCode,
    detail: data?.detail ?? text,
    details: data?.details,
  });
}

/**
 * Standardized fetch client with JWT attachment, transient GET retry,
 * and in-flight mutation deduplication.
 */
export async function apiFetch<T = any>(
  pathOrUrl: string,
  options: ApiFetchOptions = {}
): Promise<T> {
  const url = pathOrUrl.startsWith("http")
    ? pathOrUrl
    : `${API}${pathOrUrl.startsWith("/") ? "" : "/"}${pathOrUrl}`;
  const method = (options.method || "GET").toUpperCase();
  const isRead = method === "GET" || method === "HEAD";

  // In-flight mutation locking: prevent duplicate submission of the same action
  let mutationKey: string | null = null;
  if (!isRead && options.preventDuplicate !== false) {
    mutationKey =
      options.mutationKey ||
      `${method}:${url}:${typeof options.body === "string" ? options.body.slice(0, 80) : ""}`;
    if (activeMutations.has(mutationKey)) {
      throw new ApiError("A request is already in progress. Please wait.", {
        errorCode: "IN_FLIGHT_MUTATION",
      });
    }
    activeMutations.add(mutationKey);
  }

  // Safe retries: only for idempotent reads, never for mutations or auth failures
  const maxRetries = isRead ? (options.retries ?? 2) : 0;
  const baseDelay = options.retryDelayMs ?? 300;

  try {
    let attempt = 0;
    while (true) {
      attempt++;
      try {
        await ensureAuthSession(API);
        const headers: Record<string, string> = {
          ...getAuthHeaders(),
          ...((options.headers as Record<string, string>) || {}),
        };
        if (
          options.body &&
          typeof options.body === "string" &&
          !headers["Content-Type"]
        ) {
          headers["Content-Type"] = "application/json";
        }

        const res = await fetch(url, {
          ...options,
          headers,
        });

        if (!res.ok) {
          // If 401 occurs and no verified token was attached, allow a single recovery attempt
          if (res.status === 401 && !options._isAuthRetry && !getAuthToken()) {
            const freshToken = await ensureAuthSession(API);
            if (freshToken) {
              return apiFetch<T>(pathOrUrl, {
                ...options,
                _isAuthRetry: true,
              });
            }
          }

          // Retry on transient 502/503/504 for reads only
          if (
            isRead &&
            attempt <= maxRetries &&
            [502, 503, 504].includes(res.status)
          ) {
            await new Promise((r) => setTimeout(r, baseDelay * attempt));
            continue;
          }
          throw await parseApiError(res);
        }

        if (res.status === 204) {
          return undefined as unknown as T;
        }

        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          return (await res.json()) as T;
        }
        return (await res.text()) as unknown as T;
      } catch (err: any) {
        if (err instanceof ApiError) {
          throw err;
        }

        // Check if offline / network drop
        const isNetwork =
          (typeof navigator !== "undefined" && !navigator.onLine) ||
          err.name === "TypeError" ||
          /failed to fetch/i.test(err.message || "");

        // Retry safe reads on network drop
        if (isRead && attempt <= maxRetries) {
          await new Promise((r) => setTimeout(r, baseDelay * attempt));
          continue;
        }

        throw new ApiError(
          isNetwork
            ? "Unable to connect to the server. Please check your internet connection."
            : err.message || "An unexpected network error occurred.",
          {
            status: 0,
            errorCode: "NETWORK_ERROR",
            isNetworkError: true,
            detail: err.message,
          }
        );
      }
    }
  } finally {
    if (mutationKey) {
      activeMutations.delete(mutationKey);
    }
  }
}

export async function generateTrip(
    data: TripRequest
): Promise<TripResponse> {
    return apiFetch<TripResponse>("/planner/", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function suggestTravelDates(
    data: SuggestDatesParams
): Promise<{ success: boolean; data: SuggestDatesResponse }> {
    return apiFetch<{ success: boolean; data: SuggestDatesResponse }>("/planner/suggest-dates", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export async function updateTrip(
    tripId: string,
    prompt: string
): Promise<TripResponse> {
    return apiFetch<TripResponse>(`/trip/${tripId}`, {
        method: "PATCH",
        body: JSON.stringify({
            prompt,
        }),
    });
}

export async function getTrip(
    tripId: string
): Promise<TripResponse> {
    return apiFetch<TripResponse>(`/trip/${tripId}`);
}
export async function checkFavorite(
    tripId: string
): Promise<boolean> {
    const result = await apiFetch<{ favorite: boolean }>(`/trip/${tripId}/favorite`);
    return result.favorite;
}

export async function favoriteTrip(
    tripId: string
): Promise<void> {
    await apiFetch(`/trip/${tripId}/favorite`, {
        method: "POST",
    });
}

export async function unfavoriteTrip(
    tripId: string
): Promise<void> {
    await apiFetch(`/trip/${tripId}/favorite`, {
        method: "DELETE",
    });
}

export async function getTripNotes(
  tripId: string
): Promise<string[]> {
  const result = await apiFetch<{ notes: string[] }>(`/trip/${tripId}/notes`);
  return result.notes;
}

export async function addTripNote(
  tripId: string,
  note: string
): Promise<string[]> {
  const result = await apiFetch<{ notes: string[] }>(
    `/trip/${tripId}/notes?note=${encodeURIComponent(note)}`,
    {
      method: "POST",
    }
  );
  return result.notes;
}

export async function deleteTripNote(
  tripId: string,
  noteIndex: number
): Promise<void> {
  await apiFetch(`/trip/${tripId}/notes/${noteIndex}`, {
    method: "DELETE",
  });
}

export async function getTripRating(
  tripId: string
): Promise<{
  rating: number | null;
  feedback: string;
} | null> {
  const result = await apiFetch<{ rating: { rating: number | null; feedback: string } | null }>(
    `/trip/${tripId}/rating`
  );
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

  await apiFetch(`/trip/${tripId}/rating?${params.toString()}`, {
    method: "POST",
  });
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
  const result = await apiFetch<{ trips?: TripHistoryItem[] }>("/trip/history");
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
  return apiFetch("/trip/import", {
    method: "POST",
    body: JSON.stringify(tripData),
  });
}

export async function duplicateTrip(
  tripId: string
): Promise<{
  trip_id: string;
  original_trip_id: string;
  message: string;
}> {
  return apiFetch(`/trip/${tripId}/duplicate`, {
    method: "POST",
  });
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
  return apiFetch<TripComparisonResult>(`/trip/compare?${params.toString()}`);
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
  return apiFetch<TripInsightsResponse>(`/trip/${tripId}/insights`);
}

// -------------------------------------------------------------
// STEP 47: TRIP TEMPLATES SERVICE METHODS
// -------------------------------------------------------------

export async function getTemplates(): Promise<{ templates: import("../types/template").TripTemplate[] }> {
  return apiFetch<{ templates: import("../types/template").TripTemplate[] }>(`/templates`);
}

export async function getTemplate(templateId: string): Promise<import("../types/template").TripTemplate> {
  return apiFetch<import("../types/template").TripTemplate>(`/templates/${encodeURIComponent(templateId)}`);
}

export async function saveTripAsTemplate(
  tripId: string,
  name?: string,
  description?: string,
  category?: string
): Promise<{ message: string; template_id: string; name: string; destination: string; duration_days: number }> {
  return apiFetch<{ message: string; template_id: string; name: string; destination: string; duration_days: number }>(
    `/trip/${encodeURIComponent(tripId)}/template`,
    {
      method: "POST",
      body: JSON.stringify({
        name: name || "",
        description: description || "",
        category: category || "General",
      }),
    }
  );
}

export async function createTripFromTemplate(
  templateId: string,
  overrides?: { source?: string; travel_mode?: string; budget?: number }
): Promise<{ message: string; trip_id: string; template_id: string; template_name: string }> {
  return apiFetch<{ message: string; trip_id: string; template_id: string; template_name: string }>(
    `/templates/${encodeURIComponent(templateId)}/create-trip`,
    {
      method: "POST",
      body: JSON.stringify(overrides || {}),
    }
  );
}

export async function deleteTemplate(
  templateId: string
): Promise<{ message: string; template_id: string }> {
  return apiFetch<{ message: string; template_id: string }>(
    `/templates/${encodeURIComponent(templateId)}`,
    {
      method: "DELETE",
    }
  );
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
  return apiFetch<{ success: boolean; trip: any; audit: any }>(
    `/trip/${encodeURIComponent(tripId)}/replan-day`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function addRouteStop(
  tripId: string,
  day: number,
  routeStop: any,
  allowRepeat: boolean = false
): Promise<{ success: boolean; trip: any; audit: any }> {
  return apiFetch<{ success: boolean; trip: any; audit: any }>(
    `/trip/${encodeURIComponent(tripId)}/add-route-stop`,
    {
      method: "POST",
      body: JSON.stringify({ day, route_stop: routeStop, allow_repeat: allowRepeat }),
    }
  );
}

export async function switchTransportMode(
  tripId: string,
  travelMode: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  return apiFetch<{ success: boolean; trip: any; audit: any }>(
    `/trip/${encodeURIComponent(tripId)}/switch-transport`,
    {
      method: "POST",
      body: JSON.stringify({ travel_mode: travelMode }),
    }
  );
}

export async function reallocateTripBudget(
  tripId: string,
  strategy: string,
  customCategories?: Record<string, number>
): Promise<{ success: boolean; trip: any; audit: any }> {
  return apiFetch<{ success: boolean; trip: any; audit: any }>(
    `/trip/${encodeURIComponent(tripId)}/reallocate-budget`,
    {
      method: "POST",
      body: JSON.stringify({
        strategy,
        custom_categories: customCategories,
      }),
    }
  );
}

export async function castGroupVote(
  tripId: string,
  travelerName: string,
  attractionName: string,
  vote: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  return apiFetch<{ success: boolean; trip: any; audit: any }>(
    `/trip/${encodeURIComponent(tripId)}/group-vote`,
    {
      method: "POST",
      body: JSON.stringify({
        traveler_name: travelerName,
        attraction_name: attractionName,
        vote,
      }),
    }
  );
}

export async function resolveGroupConflicts(
  tripId: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  return apiFetch<{ success: boolean; trip: any; audit: any }>(
    `/trip/${encodeURIComponent(tripId)}/resolve-group-conflicts`,
    {
      method: "POST",
    }
  );
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
  return apiFetch(`/trip/${encodeURIComponent(tripId)}/assistant-chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}

export async function getTripOptimizationScore(
  tripId: string
): Promise<{ success: boolean; optimization_score: any }> {
  return apiFetch<{ success: boolean; optimization_score: any }>(
    `/trip/${encodeURIComponent(tripId)}/optimization-score`
  );
}

export async function optimizeTrip(
  tripId: string
): Promise<{ success: boolean; trip: any; audit: any }> {
  return apiFetch<{ success: boolean; trip: any; audit: any }>(
    `/trip/${encodeURIComponent(tripId)}/optimize-trip`,
    {
      method: "POST",
    }
  );
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
  const url = `/trip/${encodeURIComponent(tripId)}/attraction-alternatives?day=${encodeURIComponent(day)}&attraction_name=${encodeURIComponent(attractionName)}`;
  return apiFetch<AttractionAlternativesResponse>(url);
}

export async function executeAttractionAction(
  tripId: string,
  day: string,
  attractionName: string,
  action: "remove" | "replace",
  replacementPlace?: Partial<AlternativeAttraction> | Record<string, any>
): Promise<{ success: boolean; trip: any; message: string }> {
  return apiFetch<{ success: boolean; trip: any; message: string }>(
    `/trip/${encodeURIComponent(tripId)}/attraction-action`,
    {
      method: "POST",
      body: JSON.stringify({
        day,
        attraction_name: attractionName,
        action,
        replacement_place: replacementPlace || null,
      }),
    }
  );
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

  return apiFetch<{ success: boolean; details: PlaceDetail }>(`/places/details?${params.toString()}`);
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
  return apiFetch<TripInvitation>(`/trip/${encodeURIComponent(tripId)}/invitations`, {
    method: "POST",
    body: JSON.stringify({ role, expires_in_days: expiresInDays }),
  });
}

export async function getTripInvitations(tripId: string): Promise<TripInvitation[]> {
  const data = await apiFetch<{ invitations: TripInvitation[] }>(`/trip/${encodeURIComponent(tripId)}/invitations`);
  return data.invitations || [];
}

export async function revokeTripInvitation(tripId: string, invitationId: string): Promise<void> {
  return apiFetch<void>(`/trip/${encodeURIComponent(tripId)}/invitations/${encodeURIComponent(invitationId)}`, {
    method: "DELETE",
  });
}

export async function previewInvitation(token: string): Promise<InvitationPreview> {
  return apiFetch<InvitationPreview>(`/invitations/${encodeURIComponent(token)}`);
}

export async function acceptInvitation(token: string): Promise<{ status: string; trip_id: string; role: string }> {
  return apiFetch<{ status: string; trip_id: string; role: string }>(
    `/invitations/${encodeURIComponent(token)}/accept`,
    {
      method: "POST",
    }
  );
}

export async function declineInvitation(token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(
    `/invitations/${encodeURIComponent(token)}/decline`,
    {
      method: "POST",
    }
  );
}

export async function getLegacyTripsPreview(): Promise<any> {
  return apiFetch<any>(`/trip/legacy/preview`);
}

export async function createTripsBackup(): Promise<any> {
  return apiFetch<any>(`/trip/legacy/backup`, {
    method: "POST",
  });
}

export async function claimLegacyTrip(tripId: string): Promise<any> {
  return apiFetch<any>(`/trip/${encodeURIComponent(tripId)}/claim-legacy`, {
    method: "POST",
  });
}

export async function claimBatchLegacyTrips(tripIds?: string[]): Promise<any> {
  return apiFetch<any>(`/trip/legacy/claim-batch`, {
    method: "POST",
    body: JSON.stringify({ trip_ids: tripIds }),
  });
}

export async function getAuthUserInfo(): Promise<any> {
  return apiFetch<any>(`/auth/me`);
}

// ===========================================================================
// Step 77: Trip Group Chat & Attraction Comments
// ===========================================================================
export interface ChatMessage {
  id: string;
  message_id: string;
  trip_id: string;
  sender_id: string;
  sender_name?: string;
  content: string;
  target_type: "trip" | "attraction" | "proposal";
  target_id?: string;
  created_at: string;
  updated_at?: string;
  is_edited: boolean;
  is_deleted: boolean;
}

export interface ChatListResponse {
  messages: ChatMessage[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export async function getTripChatMessages(
  tripId: string,
  params?: {
    target_type?: string;
    target_id?: string;
    limit?: number;
    offset?: number;
  }
): Promise<ChatListResponse> {
  const query = new URLSearchParams();
  if (params?.target_type) query.append("target_type", params.target_type);
  if (params?.target_id) query.append("target_id", params.target_id);
  if (params?.limit != null) query.append("limit", String(params.limit));
  if (params?.offset != null) query.append("offset", String(params.offset));

  const url = `/chat/${encodeURIComponent(tripId)}${query.toString() ? `?${query.toString()}` : ""}`;
  return apiFetch<ChatListResponse>(url);
}

export async function sendTripChatMessage(
  tripId: string,
  content: string,
  options?: {
    target_type?: "trip" | "attraction" | "proposal";
    target_id?: string;
    sender_name?: string;
  }
): Promise<ChatMessage> {
  return apiFetch<ChatMessage>(`/chat/${encodeURIComponent(tripId)}`, {
    method: "POST",
    body: JSON.stringify({
      content,
      target_type: options?.target_type || "trip",
      target_id: options?.target_id || null,
      sender_name: options?.sender_name || null,
    }),
  });
}

export async function editTripChatMessage(
  tripId: string,
  messageId: string,
  content: string
): Promise<ChatMessage> {
  return apiFetch<ChatMessage>(`/chat/${encodeURIComponent(tripId)}/message/${encodeURIComponent(messageId)}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export async function deleteTripChatMessage(
  tripId: string,
  messageId: string
): Promise<void> {
  return apiFetch<void>(`/chat/${encodeURIComponent(tripId)}/message/${encodeURIComponent(messageId)}`, {
    method: "DELETE",
  });
}

export async function getAttractionComments(
  tripId: string,
  attractionName: string
): Promise<ChatListResponse> {
  const enc = encodeURIComponent(attractionName);
  return apiFetch<ChatListResponse>(`/trip/${encodeURIComponent(tripId)}/attractions/${enc}/comments`);
}

export async function addAttractionComment(
  tripId: string,
  attractionName: string,
  content: string,
  senderName?: string
): Promise<ChatMessage> {
  const enc = encodeURIComponent(attractionName);
  return apiFetch<ChatMessage>(`/trip/${encodeURIComponent(tripId)}/attractions/${enc}/comments`, {
    method: "POST",
    body: JSON.stringify({
      content,
      sender_name: senderName || null,
    }),
  });
}

// ===========================================================================
// Step 78: Activity Feed and In-App Notifications
// ===========================================================================
export interface ActivityEvent {
  id: string;
  trip_id: string;
  actor_id: string;
  actor_name?: string;
  event_type: string;
  title: string;
  summary: string;
  target_type?: string;
  target_id?: string;
  link?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface ActivityFeedResponse {
  activities: ActivityEvent[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface UserNotification {
  id: string;
  notification_id: string;
  user_id: string;
  trip_id: string;
  event_id?: string;
  title: string;
  message: string;
  link?: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: UserNotification[];
  total: number;
  unread_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export async function getTripActivity(
  tripId: string,
  limit: number = 50,
  offset: number = 0
): Promise<ActivityFeedResponse> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return apiFetch<ActivityFeedResponse>(`/trip/${encodeURIComponent(tripId)}/activity?${query.toString()}`);
}

export async function getUserNotifications(params?: {
  is_read?: boolean;
  trip_id?: string;
  limit?: number;
  offset?: number;
}): Promise<NotificationListResponse> {
  const query = new URLSearchParams();
  if (params?.is_read !== undefined) query.append("is_read", String(params.is_read));
  if (params?.trip_id) query.append("trip_id", params.trip_id);
  if (params?.limit != null) query.append("limit", String(params.limit));
  if (params?.offset != null) query.append("offset", String(params.offset));

  const url = `/notifications${query.toString() ? `?${query.toString()}` : ""}`;
  return apiFetch<NotificationListResponse>(url);
}

export async function getUnreadNotificationCount(tripId?: string): Promise<number> {
  const query = tripId ? `?trip_id=${encodeURIComponent(tripId)}` : "";
  try {
    const data = await apiFetch<{ unread_count: number }>(`/notifications/unread-count${query}`);
    return typeof data.unread_count === "number" ? data.unread_count : 0;
  } catch {
    return 0;
  }
}

export async function markNotificationRead(notificationId: string): Promise<void> {
  return apiFetch<void>(`/notifications/${encodeURIComponent(notificationId)}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead(tripId?: string): Promise<number> {
  const query = tripId ? `?trip_id=${encodeURIComponent(tripId)}` : "";
  const data = await apiFetch<{ affected: number }>(`/notifications/mark-all-read${query}`, {
    method: "POST",
  });
  return data?.affected || 0;
}

// -------------------------------------------------------------
// Step 79: Travel Memories and Trip Journal API
// -------------------------------------------------------------

export interface JournalEntry {
  id: string;
  trip_id: string;
  author_id: string;
  author_name?: string;
  day_number?: number;
  attraction_name?: string;
  title?: string;
  content: string;
  photo_url?: string;
  photo_filename?: string;
  is_private: boolean;
  created_at: string;
  updated_at?: string;
}

export interface JournalListResponse {
  entries: JournalEntry[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PhotoUploadResponse {
  photo_url: string;
  photo_filename: string;
  content_type: string;
  size_bytes: number;
}

export async function getJournalEntries(
  tripId: string,
  params?: {
    day_number?: number;
    attraction_name?: string;
    limit?: number;
    offset?: number;
  }
): Promise<JournalListResponse> {
  const query = new URLSearchParams();
  if (params?.day_number != null) query.append("day_number", String(params.day_number));
  if (params?.attraction_name) query.append("attraction_name", params.attraction_name);
  if (params?.limit != null) query.append("limit", String(params.limit));
  if (params?.offset != null) query.append("offset", String(params.offset));

  const url = `/trip/${encodeURIComponent(tripId)}/journal${query.toString() ? `?${query.toString()}` : ""}`;
  return apiFetch<JournalListResponse>(url);
}

export async function createJournalEntry(
  tripId: string,
  payload: {
    title?: string;
    content: string;
    day_number?: number;
    attraction_name?: string;
    photo_url?: string;
    photo_filename?: string;
    is_private?: boolean;
  }
): Promise<JournalEntry> {
  return apiFetch<JournalEntry>(`/trip/${encodeURIComponent(tripId)}/journal`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadJournalPhoto(
  tripId: string,
  file: File
): Promise<PhotoUploadResponse> {
  await ensureAuthSession(API);
  const formData = new FormData();
  formData.append("file", file);

  const authHeaders = getAuthHeaders();
  // Don't set Content-Type so browser sets multipart boundary automatically
  const headers: Record<string, string> = {};
  if (authHeaders["Authorization"]) {
    headers["Authorization"] = authHeaders["Authorization"];
  }
  if (authHeaders["X-User-ID"]) {
    headers["X-User-ID"] = authHeaders["X-User-ID"];
  }

  const res = await fetch(`${API}/trip/${encodeURIComponent(tripId)}/journal/upload-photo`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to upload photo attachment");
  }

  return await res.json();
}

export async function updateJournalEntry(
  tripId: string,
  entryId: string,
  payload: {
    title?: string;
    content?: string;
    day_number?: number;
    attraction_name?: string;
    photo_url?: string;
    photo_filename?: string;
    is_private?: boolean;
  }
): Promise<JournalEntry> {
  return apiFetch<JournalEntry>(
    `/trip/${encodeURIComponent(tripId)}/journal/${encodeURIComponent(entryId)}`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteJournalEntry(
  tripId: string,
  entryId: string
): Promise<void> {
  return apiFetch<void>(
    `/trip/${encodeURIComponent(tripId)}/journal/${encodeURIComponent(entryId)}`,
    {
      method: "DELETE",
    }
  );
}

// -------------------------------------------------------------
// Step 80: Memory Album & PDF Journal Export API
// -------------------------------------------------------------

export interface AlbumItem {
  id: string;
  trip_id: string;
  author_id: string;
  author_name?: string;
  day_number?: number;
  attraction_name?: string;
  title?: string;
  content: string;
  photo_url: string;
  photo_filename: string;
  is_private: boolean;
  created_at: string;
}

export interface MemoryAlbumResponse {
  items: AlbumItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export async function getMemoryAlbum(
  tripId: string,
  params?: {
    day_number?: number;
    limit?: number;
    offset?: number;
  }
): Promise<MemoryAlbumResponse> {
  const query = new URLSearchParams();
  if (params?.day_number != null) query.append("day_number", String(params.day_number));
  if (params?.limit != null) query.append("limit", String(params.limit));
  if (params?.offset != null) query.append("offset", String(params.offset));

  const url = `/trip/${encodeURIComponent(tripId)}/memories/album${query.toString() ? `?${query.toString()}` : ""}`;
  return apiFetch<MemoryAlbumResponse>(url);
}

export async function exportJournalPdf(
  tripId: string,
  dayNumber?: number
): Promise<Blob> {
  await ensureAuthSession(API);
  const query = new URLSearchParams();
  if (dayNumber != null) query.append("day_number", String(dayNumber));

  const url = `${API}/trip/${encodeURIComponent(tripId)}/journal/pdf${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, {
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    throw new Error(errorData?.detail || "Failed to generate journal PDF");
  }

  return await res.blob();
}






