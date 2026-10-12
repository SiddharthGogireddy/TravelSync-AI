/**
 * Manages client user identity for private trips and collaboration.
 * Uses persistent browser storage (localStorage) with a UUID.
 */

const STORAGE_KEY = "travelsync_user_id";

export function getOrCreateUserId(): string {
  if (typeof window === "undefined") {
    return "anonymous_server";
  }

  try {
    let userId = localStorage.getItem(STORAGE_KEY);
    if (!userId || !userId.trim()) {
      userId = "user_" + (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
      localStorage.setItem(STORAGE_KEY, userId);
    }
    return userId;
  } catch {
    return "user_fallback_" + Math.random().toString(36).substring(2, 10);
  }
}

export function getCurrentUserId(): string {
  return getOrCreateUserId();
}

export function getAuthHeaders(): Record<string, string> {
  return {
    "X-User-ID": getOrCreateUserId(),
  };
}
