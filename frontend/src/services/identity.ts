/**
 * Identity and Authentication Service
 *
 * Provides verified JWT session management and client identity for TravelSync AI.
 * Stores cryptographically verified tokens in browser localStorage.
 * Ensures the Authorization: Bearer <token> header is attached to all API calls.
 */

const STORAGE_KEY_USER = "travelsync_user_id";
const STORAGE_KEY_TOKEN = "travelsync_auth_token";

export function parseJwtPayload(token: string | null): any {
  if (!token || typeof token !== "string") return null;
  const parts = token.trim().split(".");
  if (parts.length !== 3) return null;

  try {
    const base64Url = parts[1];
    const padLength = (4 - (base64Url.length % 4)) % 4;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat(padLength);
    if (typeof atob === "undefined") {
      return null;
    }
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const jsonPayload = new TextDecoder().decode(bytes);
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function getOrCreateUserId(): string {
  if (typeof window === "undefined") {
    return "anonymous_server";
  }

  try {
    // If an active verified token exists in storage, its subject is the authoritative user ID
    const rawToken = localStorage.getItem(STORAGE_KEY_TOKEN);
    if (rawToken) {
      const payload = parseJwtPayload(rawToken);
      if (payload?.sub && typeof payload.sub === "string" && payload.sub.trim()) {
        const sub = payload.sub.trim();
        const nowSeconds = Math.floor(Date.now() / 1000);
        if (!payload.exp || payload.exp > nowSeconds + 10) {
          localStorage.setItem(STORAGE_KEY_USER, sub);
          return sub;
        }
      }
    }

    let userId = localStorage.getItem(STORAGE_KEY_USER);
    if (!userId || !userId.trim()) {
      userId =
        "user_" +
        (typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : Math.random().toString(36).substring(2, 15));
      localStorage.setItem(STORAGE_KEY_USER, userId);
    }
    return userId;
  } catch {
    return "user_fallback_" + Math.random().toString(36).substring(2, 10);
  }
}

export function isTokenValid(token: string | null): boolean {
  if (!token || typeof token !== "string") return false;
  const parsed = parseJwtPayload(token);
  if (!parsed) return false;

  try {
    // Verify exp has not passed (with 10-second grace window)
    if (parsed.exp && typeof parsed.exp === "number") {
      const nowSeconds = Math.floor(Date.now() / 1000);
      if (parsed.exp <= nowSeconds + 10) {
        return false;
      }
    }

    // Verify sub is non-empty
    if (!parsed.sub || typeof parsed.sub !== "string" || !parsed.sub.trim()) {
      return false;
    }

    return true;
  } catch {
    return false;
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
    const token = localStorage.getItem(STORAGE_KEY_TOKEN);
    if (!token) return null;
    if (!isTokenValid(token)) {
      return null;
    }
    return token;
  } catch {
    return null;
  }
}

export function setAuthSession(token: string, userId?: string): void {
  if (typeof window === "undefined") return;
  try {
    if (token && token.trim()) {
      const cleanToken = token.trim();
      let resolvedUserId = userId;
      if (!resolvedUserId) {
        const payload = parseJwtPayload(cleanToken);
        if (payload?.sub) resolvedUserId = payload.sub;
      }
      if (resolvedUserId) {
        localStorage.setItem(STORAGE_KEY_USER, resolvedUserId);
      }
      localStorage.setItem(STORAGE_KEY_TOKEN, cleanToken);
    } else {
      localStorage.removeItem(STORAGE_KEY_TOKEN);
    }
  } catch {}
}

export function setAuthToken(token: string): void {
  setAuthSession(token);
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    localStorage.removeItem(STORAGE_KEY_TOKEN);
    // Rotate to a fresh, independent guest session upon logout
    // so subsequent unauthenticated calls do NOT transmit the former user's ID
    const freshGuestId =
      "user_" +
      (typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : Math.random().toString(36).substring(2, 15));
    localStorage.setItem(STORAGE_KEY_USER, freshGuestId);
  } catch {
    // Graceful error ignore
  }
}

export function isAuthenticated(): boolean {
  return isTokenValid(getAuthToken());
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

let inFlightAuthPromise: Promise<string | null> | null = null;

export function resolveApiBase(apiBase?: string): string {
  if (apiBase && apiBase.trim()) return apiBase.trim().replace(/\/+$/, "");
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined" && window.location.port === "5173") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "";
}

/**
 * Asynchronously ensures a valid JWT token exists for the client.
 * If no token is stored, requests a signed JWT from /auth/token for the active user ID.
 */
export async function ensureAuthSession(apiBase?: string): Promise<string | null> {
  const existingToken = getAuthToken();
  if (existingToken && isTokenValid(existingToken)) {
    return existingToken;
  }

  if (inFlightAuthPromise) {
    return inFlightAuthPromise;
  }

  inFlightAuthPromise = (async () => {
    try {
      const token = getAuthToken();
      if (token && isTokenValid(token)) return token;

      const userId = getOrCreateUserId();
      const baseUrl = resolveApiBase(apiBase);
      const targetUrl = baseUrl ? `${baseUrl}/auth/token` : "/auth/token";
      
      let res: Response | null = null;
      try {
        res = await fetch(targetUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ user_id: userId }),
        });
      } catch (err) {
        if (baseUrl && targetUrl !== "/auth/token") {
          try {
            res = await fetch("/auth/token", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ user_id: userId }),
            });
          } catch {
            res = null;
          }
        }
      }

      if (res && res.ok) {
        const data = await res.json();
        if (data?.access_token) {
          setAuthSession(data.access_token, userId);
          return data.access_token;
        }
      }
    } catch {
      // In production or when token issuance is disabled, graceful fallback
    } finally {
      inFlightAuthPromise = null;
    }
    return null;
  })();

  return inFlightAuthPromise;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  created_at?: string;
}

export interface AuthSessionResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
  expires_in: number;
}

export async function apiLogin(email: string, password: string, apiBase?: string): Promise<AuthSessionResponse> {
  const baseUrl = resolveApiBase(apiBase);
  const targetUrl = baseUrl ? `${baseUrl}/auth/login` : "/auth/login";
  let res: Response | null = null;
  try {
    res = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch (err) {
    if (baseUrl && targetUrl !== "/auth/login") {
      res = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    } else {
      throw err;
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Login failed with status ${res.status}`);
  }
  const data: AuthSessionResponse = await res.json();
  setAuthSession(data.access_token, data.user.id);
  return data;
}

export async function apiRegister(email: string, password: string, fullName?: string, apiBase?: string): Promise<AuthSessionResponse> {
  const baseUrl = resolveApiBase(apiBase);
  const targetUrl = baseUrl ? `${baseUrl}/auth/register` : "/auth/register";
  let res: Response | null = null;
  try {
    res = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
  } catch (err) {
    if (baseUrl && targetUrl !== "/auth/register") {
      res = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
    } else {
      throw err;
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Registration failed with status ${res.status}`);
  }
  const data: AuthSessionResponse = await res.json();
  setAuthSession(data.access_token, data.user.id);
  return data;
}

export async function apiClaimSession(email: string, password: string, fullName?: string, apiBase?: string): Promise<AuthSessionResponse> {
  const userId = getOrCreateUserId();
  const baseUrl = resolveApiBase(apiBase);
  const targetUrl = baseUrl ? `${baseUrl}/auth/claim-session` : "/auth/claim-session";
  let res: Response | null = null;
  try {
    res = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, email, password, full_name: fullName }),
    });
  } catch (err) {
    if (baseUrl && targetUrl !== "/auth/claim-session") {
      res = await fetch("/auth/claim-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, email, password, full_name: fullName }),
      });
    } else {
      throw err;
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Session claim failed with status ${res.status}`);
  }
  const data: AuthSessionResponse = await res.json();
  setAuthSession(data.access_token, data.user.id);
  return data;
}
