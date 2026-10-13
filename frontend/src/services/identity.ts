/**
 * Identity and Authentication Service (Step 75.2)
 *
 * Provides verified JWT session management and client identity for TravelSync AI.
 * Stores cryptographically verified tokens in browser localStorage.
 * Ensures the Authorization: Bearer <token> header is attached to all API calls.
 */

const STORAGE_KEY_USER = "travelsync_user_id";
const STORAGE_KEY_TOKEN = "travelsync_auth_token";

export function getOrCreateUserId(): string {
  if (typeof window === "undefined") {
    return "anonymous_server";
  }

  try {
    let userId = localStorage.getItem(STORAGE_KEY_USER);
    if (!userId || !userId.trim()) {
      userId = "user_" + (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
      localStorage.setItem(STORAGE_KEY_USER, userId);
    }
    return userId;
  } catch {
    return "user_fallback_" + Math.random().toString(36).substring(2, 10);
  }
}

export function getCurrentUserId(): string {
  return getOrCreateUserId();
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return localStorage.getItem(STORAGE_KEY_TOKEN);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (token && token.trim()) {
      localStorage.setItem(STORAGE_KEY_TOKEN, token.trim());
    } else {
      localStorage.removeItem(STORAGE_KEY_TOKEN);
    }
  } catch {
    // LocalStorage quota or access error handled gracefully
  }
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    localStorage.removeItem(STORAGE_KEY_TOKEN);
  } catch {
    // Graceful error ignore
  }
}

export function isAuthenticated(): boolean {
  const token = getAuthToken();
  return Boolean(token && token.split(".").length === 3);
}

/**
 * Returns HTTP authentication headers for API requests.
 * Always includes Authorization: Bearer <token> when available,
 * and matches X-User-ID to prevent confused-deputy warnings.
 */
export function getAuthHeaders(): Record<string, string> {
  const userId = getOrCreateUserId();
  const token = getAuthToken();

  const headers: Record<string, string> = {
    "X-User-ID": userId,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Asynchronously ensures a valid JWT token exists for the client in local/dev mode.
 * If no token is stored, requests a signed JWT from /auth/token for the active user ID.
 */
export async function ensureAuthSession(apiBase: string = "http://localhost:8000"): Promise<string | null> {
  let token = getAuthToken();
  if (token) {
    return token;
  }

  const userId = getOrCreateUserId();
  try {
    const res = await fetch(`${apiBase}/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ user_id: userId }),
    });

    if (res.ok) {
      const data = await res.json();
      if (data?.access_token) {
        setAuthToken(data.access_token);
        return data.access_token;
      }
    }
  } catch (err) {
    console.warn("Could not auto-provision development auth token:", err);
  }

  return null;
}
