import { useState, useEffect } from "react";

const STORAGE_KEY_PWA_DISMISSED = "travelsync_pwa_dismissed_until";
const STORAGE_KEY_PWA_INSTALLED = "travelsync_pwa_installed";
const DISMISSAL_COOLDOWN_MS = 14 * 24 * 60 * 60 * 1000; // 14 days

export function isAppInstalled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (window.navigator as any).standalone === true;
    const recordedInstalled = localStorage.getItem(STORAGE_KEY_PWA_INSTALLED) === "true";
    return isStandalone || recordedInstalled;
  } catch {
    return false;
  }
}

export function isPromptDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const until = localStorage.getItem(STORAGE_KEY_PWA_DISMISSED);
    if (!until) return false;
    const expiry = parseInt(until, 10);
    return !isNaN(expiry) && Date.now() < expiry;
  } catch {
    return false;
  }
}

export function dismissInstallPrompt(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(
      STORAGE_KEY_PWA_DISMISSED,
      String(Date.now() + DISMISSAL_COOLDOWN_MS)
    );
  } catch {}
}

export function resetInstallPromptDismissal(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY_PWA_DISMISSED);
  } catch {}
}

export default function OfflineBanner() {
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  const [showNetworkBanner, setShowNetworkBanner] = useState<boolean>(false);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [canInstall, setCanInstall] = useState<boolean>(false);
  const [showInstallGuide, setShowInstallGuide] = useState<boolean>(false);

  useEffect(() => {
    // 1. Online / Offline network listeners
    const handleOnline = () => {
      setIsOnline(true);
      setShowNetworkBanner(true);
      const timer = setTimeout(() => setShowNetworkBanner(false), 3500);
      return () => clearTimeout(timer);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowNetworkBanner(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // 2. Installed event listener
    const handleAppInstalled = () => {
      try {
        localStorage.setItem(STORAGE_KEY_PWA_INSTALLED, "true");
      } catch {}
      setCanInstall(false);
      setDeferredPrompt(null);
    };
    window.addEventListener("appinstalled", handleAppInstalled);

    // 3. BeforeInstallPrompt listener (respects dismissal & installed state)
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);

      // Do NOT display prompt banner if app is already installed or user dismissed it
      if (!isAppInstalled() && !isPromptDismissed()) {
        setCanInstall(true);
      }
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);

    // 4. Custom event for manual installation guide trigger
    const handleOpenGuide = () => {
      setShowInstallGuide(true);
    };
    window.addEventListener("open-pwa-install-guide", handleOpenGuide);

    // Initial offline check
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      setShowNetworkBanner(true);
    }

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("appinstalled", handleAppInstalled);
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("open-pwa-install-guide", handleOpenGuide);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) {
      setShowInstallGuide(true);
      return;
    }
    deferredPrompt.prompt();
    try {
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === "accepted") {
        try {
          localStorage.setItem(STORAGE_KEY_PWA_INSTALLED, "true");
        } catch {}
        setCanInstall(false);
        setDeferredPrompt(null);
      } else {
        // If user cancelled native prompt, also apply dismissal cooldown
        dismissInstallPrompt();
        setCanInstall(false);
      }
    } catch {
      setCanInstall(false);
    }
  };

  const handleDismissPrompt = () => {
    dismissInstallPrompt();
    setCanInstall(false);
    setShowNetworkBanner(false);
  };

  const shouldRenderBanner = !isOnline || showNetworkBanner || (canInstall && !isPromptDismissed() && !isAppInstalled());

  return (
    <>
      {shouldRenderBanner && (
        <aside
          aria-label="Network status and installation"
          style={{
            position: "sticky",
            top: 0,
            zIndex: 10000,
            background: !isOnline
              ? "linear-gradient(90deg, #b91c1c 0%, #dc2626 100%)"
              : canInstall
              ? "linear-gradient(90deg, #0369a1 0%, #0284c7 100%)"
              : "linear-gradient(90deg, #059669 0%, #10b981 100%)",
            color: "#ffffff",
            padding: "10px 16px",
            fontSize: "0.88rem",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
            boxShadow: "0 2px 10px rgba(0,0,0,0.15)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span>{!isOnline ? "⚠️" : canInstall ? "📲" : "✅"}</span>
            <span>
              {!isOnline
                ? "You are currently offline. Viewing cached trips is enabled, but AI generation, chat, and uploads require an active connection."
                : canInstall
                ? "Install TravelSync AI for a full-screen, standalone mobile and desktop experience!"
                : "Connection restored! Live collaboration and syncing are active."}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {canInstall && isOnline && (
              <button
                onClick={handleInstallClick}
                style={{
                  background: "#ffffff",
                  color: "#0284c7",
                  border: "none",
                  borderRadius: 8,
                  padding: "5px 12px",
                  fontSize: "0.82rem",
                  fontWeight: 700,
                  cursor: "pointer",
                  boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
                }}
              >
                Install App
              </button>
            )}

            <button
              onClick={handleDismissPrompt}
              aria-label="Dismiss banner"
              title="Dismiss for 14 days"
              style={{
                background: "transparent",
                color: "#ffffff",
                border: "none",
                fontSize: "1.1rem",
                cursor: "pointer",
                padding: "2px 6px",
                lineHeight: 1,
                opacity: 0.9,
              }}
            >
              ✕
            </button>
          </div>
        </aside>
      )}

      {/* Manual Installation Guide Modal (accessible without forcing banner) */}
      {showInstallGuide && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10001,
            padding: "16px",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowInstallGuide(false);
          }}
        >
          <div
            style={{
              backgroundColor: "#ffffff",
              borderRadius: "16px",
              width: "100%",
              maxWidth: "480px",
              padding: "24px",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
              border: "1px solid #e2e8f0",
              textAlign: "left",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "#0f172a" }}>
                📲 Install TravelSync AI
              </h3>
              <button
                onClick={() => setShowInstallGuide(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  fontSize: "1.2rem",
                  color: "#64748b",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            <p style={{ margin: "0 0 16px 0", color: "#475569", fontSize: "0.92rem", lineHeight: 1.5 }}>
              Install TravelSync AI to launch instantly from your home screen or dock with offline itinerary caching and standalone viewing.
            </p>

            {deferredPrompt && (
              <div style={{ marginBottom: 20 }}>
                <button
                  onClick={handleInstallClick}
                  style={{
                    width: "100%",
                    padding: "12px",
                    borderRadius: "10px",
                    background: "#0284c7",
                    color: "#ffffff",
                    border: "none",
                    fontWeight: 700,
                    fontSize: "0.95rem",
                    cursor: "pointer",
                    boxShadow: "0 4px 6px -1px rgba(2, 132, 199, 0.3)",
                  }}
                >
                  Install Directly
                </button>
              </div>
            )}

            <div style={{ background: "#f8fafc", padding: "14px 16px", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontWeight: 700, fontSize: "0.85rem", color: "#334155", marginBottom: 8 }}>
                Manual Installation by Platform:
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.85rem", color: "#64748b", lineHeight: 1.6 }}>
                <li><strong>Chrome / Edge (Desktop):</strong> Click the install icon in the URL bar (⊕) or menu (⋮) → <em>Install TravelSync AI</em>.</li>
                <li><strong>Safari (iPhone / iPad):</strong> Tap the Share button (square with arrow up) → scroll down → tap <em>Add to Home Screen</em>.</li>
                <li><strong>Chrome (Android):</strong> Tap menu (⋮) → tap <em>Install app</em> or <em>Add to Home screen</em>.</li>
              </ul>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
              <button
                onClick={() => setShowInstallGuide(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "8px",
                  border: "1px solid #cbd5e1",
                  background: "#ffffff",
                  color: "#475569",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
