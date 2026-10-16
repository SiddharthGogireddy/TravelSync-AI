import { useState } from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";

import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import LoadTrip from "./pages/LoadTrip";
import TripView from "./pages/TripView";
import TripHistory from "./pages/TripHistory";
import TripComparison from "./pages/TripComparison";
import TripTemplates from "./pages/TripTemplates";
import InvitationAcceptPage from "./pages/InvitationAcceptPage";
import OfflineBanner from "./components/OfflineBanner";
import AuthModal from "./components/AuthModal";
import ThemeToggle from "./components/ThemeToggle";
import { Compass, Download } from "lucide-react";
import { generateTrip } from "./services/api";
import { getOrCreateUserId, isAuthenticated, clearAuthToken } from "./services/identity";

import type { TripRequest } from "./types/trip";
import type { TripResponse } from "./types/api";

export default function App() {
    const [data, setData] = useState<TripResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [lastRequest, setLastRequest] = useState<TripRequest | null>(null);
    const [authModalOpen, setAuthModalOpen] = useState(false);
    const [authStatus, setAuthStatus] = useState(() => ({
        loggedIn: isAuthenticated(),
        userId: getOrCreateUserId(),
    }));

    const refreshAuth = () => {
        setAuthStatus({
            loggedIn: isAuthenticated(),
            userId: getOrCreateUserId(),
        });
    };

    const handleLogout = () => {
        clearAuthToken();
        refreshAuth();
    };

    const handleSubmit = async (formData: TripRequest) => {
        try {
            setLoading(true);
            setErrorMessage(null);
            setLastRequest(formData);

            const result = await generateTrip(formData);

            if (result.trip_id) {
                window.location.href = `/trip/${result.trip_id}`;
                return;
            }

            setData(result);
        } catch (err: any) {
            console.error("Trip generation failed:", err);
            if (err?.isNetworkError) {
                setErrorMessage(
                    "Network error: Unable to reach TravelSync AI servers. Please check your internet connection."
                );
            } else if (err?.isValidationError) {
                setErrorMessage(
                    err?.message ||
                        "Validation error: Please verify your trip inputs."
                );
            } else {
                setErrorMessage(
                    err?.message ||
                        "An unexpected error occurred while planning your trip. Please try again."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <BrowserRouter>
            <div>
                <OfflineBanner />
                <nav
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "12px 24px",
                        background: "var(--nav-bg)",
                        borderBottom: "1px solid var(--nav-border)",
                        flexWrap: "wrap",
                        gap: 16,
                        transition: "background 0.2s ease, border-color 0.2s ease",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
                        <Link
                            to="/"
                            style={{
                                color: "var(--accent)",
                                textDecoration: "none",
                                fontWeight: 800,
                                fontSize: "1.15rem",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 8,
                            }}
                        >
                            <Compass size={22} style={{ color: "var(--accent)" }} />
                            <span>TravelSync AI</span>
                        </Link>
                        <Link
                            to="/"
                            style={{
                                color: "var(--text-secondary)",
                                textDecoration: "none",
                                fontWeight: 600,
                                fontSize: "0.95rem",
                            }}
                        >
                            Home
                        </Link>
                        <Link
                            to="/plan"
                            style={{
                                color: "var(--text-secondary)",
                                textDecoration: "none",
                                fontWeight: 600,
                                fontSize: "0.95rem",
                            }}
                        >
                            Plan Trip
                        </Link>
                        <Link
                            to="/trip-history"
                            style={{
                                color: "var(--text-secondary)",
                                textDecoration: "none",
                                fontWeight: 600,
                                fontSize: "0.95rem",
                            }}
                        >
                            Trip History
                        </Link>
                        <Link
                            to="/templates"
                            style={{
                                color: "var(--text-secondary)",
                                textDecoration: "none",
                                fontWeight: 600,
                                fontSize: "0.95rem",
                            }}
                        >
                            Templates
                        </Link>
                        <Link
                            to="/compare"
                            style={{
                                color: "var(--text-secondary)",
                                textDecoration: "none",
                                fontWeight: 600,
                                fontSize: "0.95rem",
                            }}
                        >
                            Compare Trips
                        </Link>
                        <Link
                            to="/load-trip"
                            style={{
                                color: "var(--text-secondary)",
                                textDecoration: "none",
                                fontWeight: 600,
                                fontSize: "0.95rem",
                            }}
                        >
                            Load / Restore
                        </Link>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        <ThemeToggle />

                        <button
                            type="button"
                            onClick={() => window.dispatchEvent(new CustomEvent("open-pwa-install-guide"))}
                            title="Open PWA installation instructions"
                            style={{
                                padding: "6px 12px",
                                borderRadius: "8px",
                                border: "1px solid var(--border)",
                                background: "var(--card-bg)",
                                color: "var(--text-secondary)",
                                fontWeight: 600,
                                fontSize: "0.82rem",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6,
                            }}
                        >
                            <Download size={14} />
                            <span>Install App</span>
                        </button>

                        <span
                            style={{
                                fontSize: "0.85rem",
                                color: "var(--text-muted)",
                                background: "var(--code-bg)",
                                border: "1px solid var(--border)",
                                padding: "5px 12px",
                                borderRadius: "9999px",
                            }}
                        >
                            {authStatus.loggedIn ? "Account" : "Guest"}:{" "}
                            <strong style={{ color: "var(--text-h)" }}>
                                {authStatus.userId.slice(0, 16)}...
                            </strong>
                        </span>

                        {authStatus.loggedIn ? (
                            <button
                                type="button"
                                onClick={handleLogout}
                                style={{
                                    padding: "6px 14px",
                                    borderRadius: "8px",
                                    border: "1px solid var(--border)",
                                    background: "var(--card-bg)",
                                    color: "var(--text-secondary)",
                                    fontWeight: 600,
                                    fontSize: "0.875rem",
                                    cursor: "pointer",
                                }}
                            >
                                Log Out
                            </button>
                        ) : (
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <Link
                                    to="/login"
                                    style={{
                                        padding: "6px 14px",
                                        borderRadius: "8px",
                                        border: "1px solid var(--border)",
                                        background: "var(--card-bg)",
                                        color: "var(--text-secondary)",
                                        fontWeight: 600,
                                        fontSize: "0.875rem",
                                        textDecoration: "none",
                                    }}
                                >
                                    Sign In
                                </Link>
                                <Link
                                    to="/signup"
                                    style={{
                                        padding: "6px 14px",
                                        borderRadius: "8px",
                                        border: "none",
                                        background: "var(--accent)",
                                        color: "#ffffff",
                                        fontWeight: 600,
                                        fontSize: "0.875rem",
                                        textDecoration: "none",
                                        boxShadow: "0 1px 2px rgba(79, 70, 229, 0.2)",
                                    }}
                                >
                                    Register
                                </Link>
                            </div>
                        )}
                    </div>
                </nav>

                <AuthModal
                    isOpen={authModalOpen}
                    onClose={() => setAuthModalOpen(false)}
                    onSuccess={refreshAuth}
                />

                <Routes>
                    <Route
                        path="/"
                        element={
                            <LandingPage
                                authStatus={authStatus}
                                onPlanTrip={handleSubmit}
                                loading={loading}
                                errorMessage={errorMessage}
                                lastRequest={lastRequest}
                                data={data}
                            />
                        }
                    />
                    <Route
                        path="/plan"
                        element={
                            <LandingPage
                                authStatus={authStatus}
                                onPlanTrip={handleSubmit}
                                loading={loading}
                                errorMessage={errorMessage}
                                lastRequest={lastRequest}
                                data={data}
                            />
                        }
                    />
                    <Route
                        path="/login"
                        element={<LoginPage onAuthSuccess={refreshAuth} />}
                    />
                    <Route
                        path="/signup"
                        element={<SignupPage onAuthSuccess={refreshAuth} />}
                    />
                    <Route
                        path="/register"
                        element={<SignupPage onAuthSuccess={refreshAuth} />}
                    />
                    <Route
                        path="/trip-history"
                        element={<TripHistory />}
                    />
                    <Route path="/trip/:id" element={<TripView />} />
                    <Route path="/invite/:token" element={<InvitationAcceptPage />} />
                    <Route
                        path="/load-trip"
                        element={<LoadTrip />}
                    />
                    <Route
                        path="/templates"
                        element={<TripTemplates />}
                    />
                    <Route
                        path="/compare"
                        element={<TripComparison />}
                    />
                </Routes>
            </div>
        </BrowserRouter>
    );
}