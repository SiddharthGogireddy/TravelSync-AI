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


      <TravelerConflicts
        conflicts={trip.traveler_conflicts}
      />


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

    </div>
  );
}