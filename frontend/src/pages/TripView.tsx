import { useEffect, useState, useRef } from "react";

import BudgetAlerts from "../components/BudgetAlerts";
import AddExpenseModal from "../components/AddExpenseModal";
import BudgetBreakdown from "../components/BudgetBreakdown";
import BudgetCard from "../components/BudgetCard";
import BudgetPieChart from "../components/BudgetPieChart";
import BudgetStatus from "../components/BudgetStatus";
import Dashboard from "../components/Dashboard";
import DayCard from "../components/DayCard";
import ExpenseCard from "../components/ExpenseCard";
import ExpenseTable from "../components/ExpenseTable";
import MapView from "../components/MapView";
import SettlementCard from "../components/SettlementCard";
import WeatherCard from "../components/WeatherCard";
import TravelerConflicts from "../components/TravelerConflicts";
import TripInsightsCard from "../components/TripInsightsCard";

import { useNavigate } from "react-router-dom";

import {
  addExpense,
  getExpenses,
} from "../services/expense";

import {
  updateTrip,
  checkFavorite,
  favoriteTrip,
  unfavoriteTrip,
  getTripNotes,
  addTripNote,
  deleteTripNote,
  getTripRating,
  
  rateTrip,
  downloadTripPdf,
  exportTrip,
  importTrip,
  duplicateTrip,
  saveTripAsTemplate,
} from "../services/api";

import type {
  Place,
  Traveler,
  TripResponse,
  Weather,
} from "../types/api";

import type { ExpenseResponse } from "../types/expense";


function getTripIdFromUrl(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const match = window.location.pathname.match(
    /\/trip\/([^/]+)/
  );

  return match?.[1];
}


export default function TripView() {
  const [editPrompt, setEditPrompt] = useState("");
  const [updating, setUpdating] = useState(false);

  const navigate = useNavigate();

  const [selectedPlace, setSelectedPlace] =
    useState<Place | null>(null);

  const tripId = getTripIdFromUrl();

  const [isFavorite, setIsFavorite] =
    useState(false);
  const [notes, setNotes] = useState<string[]>([]);
  const [newNote, setNewNote] = useState("");
  const [data, setData] =
    useState<TripResponse | null>(null);

  const [expenseData, setExpenseData] =
    useState<ExpenseResponse | null>(null);
  const [tripRating, setTripRating] = useState<number | null>(null);
  const [ratingFeedback, setRatingFeedback] = useState("");
  const [ratingSaved, setRatingSaved] = useState(false);
  const importFileInputRef = useRef<HTMLInputElement>(null);

  const handleQuickImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);
        const res = await importTrip(parsed);
        alert(`Trip restored successfully! ID: ${res.trip_id}`);
        navigate(`/trip/${res.trip_id}`);
      } catch (err: any) {
        alert(
          err instanceof SyntaxError
            ? "Malformed JSON: invalid syntax"
            : err.message || "Failed to import trip"
        );
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const [duplicating, setDuplicating] = useState(false);

  const handleDuplicateTrip = async () => {
    if (!tripId) return;
    try {
      setDuplicating(true);
      const res = await duplicateTrip(tripId);
      alert(`Trip duplicated successfully! New ID: ${res.trip_id}`);
      navigate(`/trip/${res.trip_id}`);
    } catch (err: any) {
      alert(err.message || "Failed to duplicate trip");
    } finally {
      setDuplicating(false);
    }
  };

  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDesc, setTemplateDesc] = useState("");
  const [templateCategory, setTemplateCategory] = useState("General");
  const [savingTemplate, setSavingTemplate] = useState(false);

  const handleSaveAsTemplate = async () => {
    if (!tripId) return;
    try {
      setSavingTemplate(true);
      const res = await saveTripAsTemplate(
        tripId,
        templateName.trim() || undefined,
        templateDesc.trim() || undefined,
        templateCategory
      );
      alert(`Success! Template "${res.name}" created. You can reuse it anytime from the Templates tab.`);
      setShowTemplateModal(false);
      setTemplateName("");
      setTemplateDesc("");
    } catch (err: any) {
      alert(err.message || "Failed to create template from trip");
    } finally {
      setSavingTemplate(false);
    }
  };


  /*
   * Check whether this trip is already a favorite.
   */
  useEffect(() => {
    if (!tripId) return;

    checkFavorite(tripId)
      .then(setIsFavorite)
      .catch(() => {});
  }, [tripId]);


  /*
   * Load trip and expense data.
   */
  useEffect(() => {
    const id = getTripIdFromUrl();

    if (!id) return;

    async function fetchTrip(tripId: string) {
      try {
        const res = await fetch(
          `http://127.0.0.1:8000/trip/${tripId}`
        );

        if (!res.ok) {
          throw new Error("Failed to load trip");
        }

        const json: TripResponse =
          await res.json();

        setData(json);

        const expenses =
          await getExpenses(tripId);

        setExpenseData(expenses);
        const savedNotes =
  await getTripNotes(tripId);
  

setNotes(savedNotes);
const savedRating =
  await getTripRating(tripId);

if (savedRating) {
  setTripRating(savedRating.rating);
  setRatingFeedback(savedRating.feedback);
}
      } catch (err) {
        console.error(err);
      }
    }

    fetchTrip(id);
  }, []);


  /*
   * All hooks must be above this conditional return.
   */
  if (!tripId) {
    return <p>Trip ID not found</p>;
  }


  const handleTripEdit = async () => {
    if (!editPrompt.trim()) {
      return;
    }

    try {
      setUpdating(true);

      const updatedTrip =
        await updateTrip(
          tripId,
          editPrompt
        );

      setData(updatedTrip);
      setEditPrompt("");

    } catch (error) {
      console.error(
        "Trip update failed:",
        error
      );
    } finally {
      setUpdating(false);
    }
  };


  
    async function handleAddExpense(
  title: string,
  amount: number,
  paidBy: string
) {if (!tripId) {
    return;
  }


  await addExpense(tripId, {
    title,
    amount,
    paid_by: paidBy,
  });

  const updated = await getExpenses(tripId);

  setExpenseData(updated);
}


  async function handleRegenerateDay(
    day: string
  ) {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/trip/${tripId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prompt: `Regenerate Day ${day}`,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Failed to regenerate Day ${day}`
        );
      }

      const updatedTrip: TripResponse =
        await response.json();

      setData(updatedTrip);

    } catch (error) {
      console.error(
        "Regeneration failed:",
        error
      );
    }
  }


  if (!data) {
    return <div>Loading...</div>;
  }


  const { trip, dashboard } = data;


  const normalizedWeather: Weather[] =
    trip.weather.map((w) => ({
      ...w,
      description: w.description ?? "",
    }));

  const isMulti = (trip as any)?.is_multi_destination || ((trip as any)?.destinations && (trip as any).destinations.length > 1);
  const destinationsList = (trip as any)?.destinations || [];
  const travelLegs = (trip as any)?.inter_destination_travel || [];
  const constraintAnalysis = (trip as any)?.constraint_analysis;



  return (
    <div className="page-container">

      <button
        type="button"
        className="plan-another-button"
        onClick={() =>
          navigate("/", {
            state: {
              trip: trip,
            },
          })
        }
      >
        ← Plan Another Trip
      </button>


      <Dashboard dashboard={dashboard} />


      {/* Share Trip */}
      <button
        onClick={() => {
          const url =
            `${window.location.origin}/trip/${tripId}`;

          navigator.clipboard.writeText(url);

          alert("Trip link copied!");
        }}
      >
        Share Trip
      </button>


      {/* Favorite Trip */}
      <button
        onClick={async () => {
          if (isFavorite) {
            await unfavoriteTrip(tripId);
            setIsFavorite(false);
          } else {
            await favoriteTrip(tripId);
            setIsFavorite(true);
          }
        }}
      >
        {isFavorite
          ? "★ Favorited"
          : "☆ Favorite"}
      </button>


      {/* Export Trip */}
      <button
        onClick={() => {
          if (tripId) {
            exportTrip(tripId);
          }
        }}
      >
        Export Trip
      </button>


      {/* Import Trip */}
      <input
        type="file"
        ref={importFileInputRef}
        accept=".json,application/json"
        style={{ display: "none" }}
        onChange={handleQuickImportFile}
      />
      <button
        onClick={() => {
          importFileInputRef.current?.click();
        }}
      >
        Import Trip
      </button>


      {/* Duplicate Trip */}
      <button
        onClick={handleDuplicateTrip}
        disabled={duplicating}
      >
        {duplicating ? "Duplicating..." : "Duplicate Trip"}
      </button>


      {/* Save as Template */}
      <button
        onClick={() => {
          if (dashboard) {
            setTemplateName(`${dashboard.days || 1}-Day ${dashboard.destination || "Trip"} Template`);
          }
          setShowTemplateModal(true);
        }}
      >
        Save as Template
      </button>


      {/* Compare Trip */}
      <button
        onClick={() => {
          if (tripId) {
            navigate(`/compare?trip1=${tripId}`);
          }
        }}
      >
        Compare Trip
      </button>

      {/* Trip Analytics & Insights */}
      <TripInsightsCard tripId={tripId} />

      {/* Multi-Destination Tour Route Card */}
      {isMulti && (
        <div
          style={{
            background: "#ffffff",
            border: "1px solid #e0e7ff",
            borderRadius: 12,
            padding: "20px 24px",
            margin: "24px 0",
            boxShadow: "0 4px 6px -1px rgba(79, 70, 229, 0.08)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.25rem", color: "#1e1b4b", display: "flex", alignItems: "center", gap: 8 }}>
                <span>🗺️</span> Multi-Destination Travel Circuit
              </h3>
              <p style={{ margin: 0, color: "#64748b", fontSize: "0.88rem" }}>
                Coordinated itinerary spanning {destinationsList.length} destinations
              </p>
            </div>
            <span
              style={{
                background: "#e0e7ff",
                color: "#4338ca",
                padding: "6px 14px",
                borderRadius: 20,
                fontSize: "0.82rem",
                fontWeight: 700,
              }}
            >
              {destinationsList.length} Cities • {dashboard.days} Days Total
            </span>
          </div>

          {/* Destinations Timeline / Steps */}
          <div style={{ display: "grid", gridTemplateColumns: `repeat(auto-fit, minmax(220px, 1fr))`, gap: 14, marginBottom: 20 }}>
            {destinationsList.map((stop: any, idx: number) => (
              <div
                key={idx}
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: 10,
                  padding: "14px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#4f46e5", textTransform: "uppercase" }}>
                    Stop {idx + 1}
                  </span>
                  <span style={{ background: "#ecfdf5", color: "#059669", fontSize: "0.78rem", fontWeight: 700, padding: "2px 8px", borderRadius: 10 }}>
                    Day {stop.start_day} - {stop.end_day} ({stop.days}d)
                  </span>
                </div>
                <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "1.02rem", marginBottom: 4 }}>
                  {stop.name}
                </div>
                {stop.attraction_count !== undefined && (
                  <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
                    📍 {stop.attraction_count} attractions scheduled
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Travel Between Destinations Legs */}
          {travelLegs.length > 0 && (
            <div>
              <h4 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: "#334155" }}>
                🚗 Inter-Destination Travel Legs
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {travelLegs.map((leg: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      background: "#f1f5f9",
                      borderRadius: 8,
                      padding: "10px 14px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: "0.88rem",
                      flexWrap: "wrap",
                      gap: 8,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 600, color: "#0f172a" }}>
                        Leg {leg.leg_index}: {leg.from_location?.split(",")[0]} ➔ {leg.to_location?.split(",")[0]}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 16, color: "#475569", fontSize: "0.82rem" }}>
                      <span>📏 <strong>{leg.distance_km} km</strong></span>
                      <span>⏱️ <strong>{leg.duration_hours} hrs</strong></span>
                      <span>🚘 <strong>{leg.travel_mode?.toUpperCase()}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}


      <TravelerConflicts
        conflicts={trip.traveler_conflicts}
      />

      {/* Planning Constraints Audit Card */}
      {constraintAnalysis && (
        <div
          style={{
            background: "#ffffff",
            border: constraintAnalysis.violations?.length ? "1px solid #fecaca" : "1px solid #bbf7d0",
            borderRadius: 12,
            padding: "20px 24px",
            margin: "24px 0",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.2rem", color: "#0f172a", display: "flex", alignItems: "center", gap: 8 }}>
                <span>🎯</span> Planning Constraints Audit
              </h3>
              <p style={{ margin: 0, color: "#64748b", fontSize: "0.86rem" }}>
                Verified adherence to custom budget, distance limits, and location requirements
              </p>
            </div>
            <span
              style={{
                background: constraintAnalysis.violations?.length ? "#fee2e2" : "#dcfce7",
                color: constraintAnalysis.violations?.length ? "#991b1b" : "#166534",
                padding: "6px 14px",
                borderRadius: 20,
                fontSize: "0.82rem",
                fontWeight: 700,
              }}
            >
              {constraintAnalysis.violations?.length ? "⚠️ Constraints Adjusted" : "✓ All Constraints Met"}
            </span>
          </div>

          {/* Satisfied items pills */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
            {constraintAnalysis.satisfied?.budget !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.budget ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.budget ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.budget ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.budget ? "✓ Budget Respected" : "✕ Budget Exceeded"}
              </span>
            )}
            {constraintAnalysis.satisfied?.distance !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.distance ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.distance ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.distance ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.distance ? "✓ Daily Distance Capped" : "✕ Distance Exceeded"}
              </span>
            )}
            {constraintAnalysis.satisfied?.must_visit !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.must_visit ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.must_visit ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.must_visit ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.must_visit ? "✓ Must-Visit Scheduled" : "✕ Must-Visit Missing"}
              </span>
            )}
            {constraintAnalysis.satisfied?.avoided_locations !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.avoided_locations ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.avoided_locations ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.avoided_locations ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.avoided_locations ? "✓ Avoided Locations Excluded" : "✕ Avoided Visited"}
              </span>
            )}
          </div>

          {/* Details breakdown */}
          {constraintAnalysis.details && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, fontSize: "0.85rem", background: "#f8fafc", padding: 12, borderRadius: 8, marginBottom: 12 }}>
              {constraintAnalysis.details.max_daily_distance_km && (
                <div>
                  <span style={{ color: "#64748b" }}>Daily Distance Limit: </span>
                  <strong>{constraintAnalysis.details.max_daily_distance_km} km</strong> (Peak: {constraintAnalysis.details.max_observed_day_distance_km} km)
                </div>
              )}
              {constraintAnalysis.details.max_budget && (
                <div>
                  <span style={{ color: "#64748b" }}>Budget Cap: </span>
                  <strong>${constraintAnalysis.details.max_budget}</strong> (Est: ${constraintAnalysis.details.estimated_total_cost})
                </div>
              )}
              {constraintAnalysis.details.must_visit_included?.length > 0 && (
                <div>
                  <span style={{ color: "#64748b" }}>Must-Visits Added: </span>
                  <strong>{constraintAnalysis.details.must_visit_included.join(", ")}</strong>
                </div>
              )}
              {constraintAnalysis.details.avoided_locations_excluded?.length > 0 && (
                <div>
                  <span style={{ color: "#64748b" }}>Locations Avoided: </span>
                  <strong>{constraintAnalysis.details.avoided_locations_excluded.join(", ")}</strong>
                </div>
              )}
            </div>
          )}

          {constraintAnalysis.explanation && (
            <div style={{ fontSize: "0.85rem", color: "#475569", fontStyle: "italic", borderTop: "1px solid #f1f5f9", paddingTop: 8 }}>
              💡 {constraintAnalysis.explanation}
            </div>
          )}

          {constraintAnalysis.violations?.length > 0 && (
            <div style={{ marginTop: 10, padding: "8px 12px", background: "#fef2f2", borderRadius: 6, border: "1px solid #fecaca" }}>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#991b1b", marginBottom: 4 }}>Note on Constraints:</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.82rem", color: "#b91c1c" }}>
                {constraintAnalysis.violations.map((v: string, i: number) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}



      <div className="section">

        <h2 className="section-title">
          Budget Overview
        </h2>

        <BudgetCard
          budget={trip.budget}
        />

        <BudgetStatus
          status={trip.budget.status}
          remaining={trip.budget.remaining}
        />

        <BudgetBreakdown
          categories={trip.budget.categories}
        />

        <BudgetPieChart
          categories={trip.budget.categories}
        />

      </div>


      <div className="section card">

        <h2 className="section-title">
          Travelers
        </h2>

        {trip.travelers.map(
          (
            traveler: Traveler,
            index: number
          ) => (
            <div key={index}>
              <strong>
                {traveler.name}
              </strong>

              {" - "}

              {traveler.budget}
            </div>
          )
        )}

      </div>


      <div className="section">

        <h2 className="section-title">
          Weather
        </h2>

        {normalizedWeather.map(
          (weather, index) => (
            <WeatherCard
              key={index}
              weather={weather}
            />
          )
        )}


        {trip.transport && (
          <div className="card">

            <h3>Transportation</h3>

            <p>
              <strong>
                {trip.transport.label}
              </strong>
            </p>

            <p>
              {trip.transport.description}
            </p>

            <div className="transport-summary">

              <div>
                <strong>
                  {trip.transport.distance_km} km
                </strong>

                <span>
                  Total Distance
                </span>
              </div>

              <div>
                <strong>
                  {trip.transport.duration_hours} hrs
                </strong>

                <span>
                  Total Duration
                </span>
              </div>

            </div>


            <div className="transport-legs">

              {trip.transport.legs.map(
                (leg, index) => (

                  <div
                    key={index}
                    className="transport-leg"
                  >

                    <div>

                      <strong>
                        {leg.type}
                      </strong>

                      <p>
                        {leg.from} → {leg.to}
                      </p>

                    </div>


                    <div>

                      <span>
                        {leg.distance_km} km
                      </span>

                      <span>
                        {leg.duration_hours} hrs
                      </span>

                    </div>

                  </div>

                )
              )}

            </div>

          </div>
        )}

      </div>

        <div className="section card">
  <h2>Trip Notes</h2>

  <div style={{ display: "flex", gap: "10px" }}>
    <input
      type="text"
      value={newNote}
      onChange={(e) => setNewNote(e.target.value)}
      placeholder="Add a note..."
      style={{
        flex: 1,
        padding: "10px",
      }}
    />

    <button
      onClick={async () => {
        if (!newNote.trim()) return;

        try {
          const updatedNotes = await addTripNote(
            tripId,
            newNote
          );

          setNotes(updatedNotes);
          setNewNote("");
        } catch (error) {
          console.error(
            "Failed to add note:",
            error
          );
        }
      }}
    >
      Add Note
    </button>
  </div>

  {notes.length === 0 ? (
    <p>No notes yet.</p>
  ) : (
    <ul>
      {notes.map((note, index) => (
        <li key={index}>
          <span>{note}</span>

          <button
            onClick={async () => {
              try {
                await deleteTripNote(
                  tripId,
                  index
                );

                const updatedNotes =
                  await getTripNotes(tripId);

                setNotes(updatedNotes);
              } catch (error) {
                console.error(
                  "Failed to delete note:",
                  error
                );
              }
            }}
            style={{
              marginLeft: "10px",
            }}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  )}
</div>
      <div className="section card">

        <h2>Edit Your Trip</h2>

        <p>
          Tell TravelSync AI what you want to change.
        </p>

        <textarea
          value={editPrompt}
          onChange={(e) =>
            setEditPrompt(e.target.value)
          }
          placeholder='Try: "Add Charminar"'
          rows={3}
          style={{
            width: "100%",
            padding: "10px",
            marginTop: "10px",
            marginBottom: "10px",
            resize: "vertical",
          }}
        />

        <button
          className="regenerate-button"
          onClick={handleTripEdit}
          disabled={
            updating ||
            !editPrompt.trim()
          }
        >
          {updating
            ? "Updating..."
            : "Apply Changes"}
        </button>

        <p style={{ marginTop: "10px" }}>
          Try: "Add Charminar", "Remove Charminar",
          "Regenerate Day 2", or
          "Keep budget under ₹30000"
        </p>

      </div>


      <div className="section">

        <h2 className="section-title">
          Daily Plan
        </h2>

        {trip.day_schedule &&
          Object.entries(
            trip.day_schedule
          ).map(
            ([day, places]) => (

              <DayCard
                key={day}
                day={day}
                places={places}
                TravelMode={trip.transport.mode}
                mealsAndBreaks={(trip as any)?.meals_and_breaks?.[day]}
                onSelect={
                  setSelectedPlace
                }
                onRegenerate={
                  handleRegenerateDay
                }
              />


            )
          )}

      </div>


      <div className="section">

        <h2 className="section-title">
          Map
        </h2>

        <MapView
          lat={
            trip.destination_location.lat
          }
          lon={
            trip.destination_location.lon
          }
          places={trip.places}
          hotels={trip.hotels}
          selectedPlace={
            selectedPlace
          }
          routeCoordinates={
            trip.route_coordinates
          }
        />

      </div>


      {data.itinerary?.days && (
        <div className="section">

          <h2 className="section-title">
            AI Itinerary
          </h2>

          {data.itinerary.days.map(
            (day) => (

              <div
                key={day.day}
                className="card"
              >

                <h3>
                  Day {day.day}:{" "}
                  {day.title}
                </h3>

                <h4>
                  Activities
                </h4>

                <ul>
                  {day.activities.map(
                    (
                      activity,
                      index
                    ) => (
                      <li key={index}>
                        {activity}
                      </li>
                    )
                  )}
                </ul>


                <h4>
                  Food
                </h4>

                <ul>
                  {day.food.map(
                    (food, index) => (
                      <li key={index}>
                        {food}
                      </li>
                    )
                  )}
                </ul>


                <p>
                  <strong>
                    Budget:
                  </strong>{" "}
                  {day.budget}
                </p>

              </div>

            )
          )}

        </div>
      )}


      <div className="section">

        <AddExpenseModal
          travelers={trip.travelers.map(
            (traveler) =>
              traveler.name
          )}
          onAdd={handleAddExpense}
        />

      </div>


      {expenseData && (
        <div className="section">

          <BudgetAlerts
            alerts={expenseData.alerts}
          />

          <h2 className="section-title">
            Trip Expenses
          </h2>

          <ExpenseCard
            total={
              expenseData.expenses.reduce(
                (sum, expense) =>
                  sum + expense.amount,
                0
              )
            }
          />

          <ExpenseTable
            expenses={
              expenseData.expenses
            }
          />

          <SettlementCard
            settlements={
              expenseData.settlements
            }
          />

        </div>
      )}

      <div className="section card">
  <h2>Rate This Trip</h2>

 <div>
  {[1, 2, 3, 4, 5].map((star) => (
    <button
      key={star}
      type="button"
      onClick={() => {
        setTripRating(star);
        setRatingSaved(false);
      }}
      style={{
        fontSize: "32px",
        padding: "4px 8px",
        border: "none",
        background: "transparent",
        cursor: "pointer",
        color:
          tripRating !== null && star <= tripRating
            ? "gold"
            : "gray",
      }}
    >
      {tripRating !== null && star <= tripRating
        ? "★"
        : "☆"}
    </button>
  ))}
</div>

  <textarea
    value={ratingFeedback}
    onChange={(e) => {
      setRatingFeedback(e.target.value);
      setRatingSaved(false);
    }}
    placeholder="Optional feedback..."
    rows={3}
    style={{
      width: "100%",
      marginTop: "10px",
      padding: "10px",
    }}
  />

  <button
    type="button"
    disabled={tripRating === null}
    onClick={async () => {
      if (tripRating === null) return;

      try {
        await rateTrip(
          tripId,
          tripRating,
          ratingFeedback
        );

        setRatingSaved(true);
      } catch (error) {
        console.error(
          "Failed to save rating:",
          error
        );
      }
    }}
    style={{
      marginTop: "10px",
    }}
  >
    Save Rating
  </button>

  {ratingSaved && (
    <p>Rating saved successfully.</p>
  )}
</div>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: 12,
          marginTop: 30,
        }}
      >

        <button
          className="download-button"
          onClick={handleDuplicateTrip}
          disabled={duplicating}
          style={{
            background: "#0284c7",
          }}
        >
          {duplicating ? "Duplicating..." : "Duplicate Trip"}
        </button>

        <button
          className="download-button"
          onClick={() => {
            if (dashboard) {
              setTemplateName(`${dashboard.days || 1}-Day ${dashboard.destination || "Trip"} Template`);
            }
            setShowTemplateModal(true);
          }}
          style={{
            background: "#7c3aed",
          }}
        >
          Save as Template
        </button>

        <button
          className="download-button"
          onClick={() => {
            if (tripId) {
              exportTrip(tripId);
            }
          }}
          style={{
            background: "#4f46e5",
          }}
        >
          Export Trip
        </button>

        <button
          className="download-button"
          onClick={() => {
            if (tripId) {
              downloadTripPdf(tripId);
            }
          }}
        >
          Download PDF
        </button>

      </div>

      {/* SAVE TRIP AS TEMPLATE MODAL */}
      {showTemplateModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "#fff",
              borderRadius: 12,
              padding: 24,
              maxWidth: 480,
              width: "100%",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)",
            }}
          >
            <h3 style={{ margin: "0 0 8px", fontSize: "1.25rem", color: "#1e293b" }}>
              Save Trip as Template
            </h3>
            <p style={{ margin: "0 0 16px", color: "#64748b", fontSize: "0.88rem" }}>
              Make this itinerary a reusable blueprint for future trip planning.
            </p>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>
                Template Name
              </label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="e.g. 3-Day Goa Leisure & Beach Escape"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>
                Category
              </label>
              <select
                value={templateCategory}
                onChange={(e) => setTemplateCategory(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: "#fff",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              >
                <option value="General">General</option>
                <option value="Weekend Getaway">Weekend Getaway</option>
                <option value="Heritage & Culture">Heritage & Culture</option>
                <option value="Beach & Leisure">Beach & Leisure</option>
                <option value="Adventure">Adventure</option>
                <option value="Family Friendly">Family Friendly</option>
              </select>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>
                Description (Optional)
              </label>
              <textarea
                value={templateDesc}
                onChange={(e) => setTemplateDesc(e.target.value)}
                placeholder="Describe what makes this template great..."
                rows={3}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setShowTemplateModal(false)}
                disabled={savingTemplate}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: "#fff",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                  color: "#475569",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAsTemplate}
                disabled={savingTemplate}
                style={{
                  padding: "8px 18px",
                  borderRadius: 6,
                  border: "none",
                  background: "#7c3aed",
                  color: "#fff",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                }}
              >
                {savingTemplate ? "Saving..." : "Save Template"}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}