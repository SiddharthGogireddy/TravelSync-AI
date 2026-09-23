import { useEffect, useState } from "react";

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
import { useNavigate } from "react-router-dom";
import { addExpense, getExpenses } from "../services/expense";
import { updateTrip } from "../services/api";
import type {
  Place,
  Traveler,
  TripResponse,
  Weather,
} from "../types/api";

import type { ExpenseResponse } from "../types/expense";

function getTripIdFromUrl(): string | undefined {
  if (typeof window === "undefined") return undefined;

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

  const [data, setData] =
    useState<TripResponse | null>(null);

  const [expenseData, setExpenseData] =
    useState<ExpenseResponse | null>(null);
  const handleTripEdit = async () => {
    if (!editPrompt.trim()) {
        return;
    }

    const tripId = getTripIdFromUrl();

    if (!tripId) {
        return;
    }

    try {
        setUpdating(true);

        const updatedTrip = await updateTrip(
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
  ) {
    const tripId = getTripIdFromUrl();

    if (!tripId) return;

    await addExpense(tripId, {
      title,
      amount,
      paid_by: paidBy,
    });

    const updated =
      await getExpenses(tripId);

    setExpenseData(updated);
  }
  async function handleRegenerateDay(day: string) {
    const tripId = getTripIdFromUrl();

    if (!tripId) return;

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
  
  useEffect(() => {
    const tripId = getTripIdFromUrl();

    if (!tripId) return;

    async function fetchTrip(id: string) {
      try {
        const res = await fetch(
          `http://127.0.0.1:8000/trip/${id}`
        );

        const json: TripResponse =
          await res.json();

        setData(json);

        const expenses =
          await getExpenses(id);

        setExpenseData(expenses);
      } catch (err) {
        console.error(err);
      }
    }

    fetchTrip(tripId);
  }, []);

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
        
      <div className="section">
        <h2 className="section-title">
          Budget Overview
        </h2>

        <BudgetCard budget={trip.budget} />

        <BudgetStatus
    status={trip.budget.status}
    remaining={trip.budget.remaining}
/>

        <BudgetBreakdown
          categories={
            trip.budget.categories
          }
        />

        <BudgetPieChart
          categories={
            trip.budget.categories
          }
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
            <strong>{trip.transport.label}</strong>
        </p>

        <p>{trip.transport.description}</p>

        <div className="transport-summary">
            <div>
                <strong>{trip.transport.distance_km} km</strong>
                <span>Total Distance</span>
            </div>

            <div>
                <strong>{trip.transport.duration_hours} hrs</strong>
                <span>Total Duration</span>
            </div>
        </div>

        <div className="transport-legs">
            {trip.transport.legs.map((leg, index) => (
                <div key={index} className="transport-leg">
                    <div>
                        <strong>{leg.type}</strong>
                        <p>
                            {leg.from} → {leg.to}
                        </p>
                    </div>

                    <div>
                        <span>{leg.distance_km} km</span>
                        <span>{leg.duration_hours} hrs</span>
                    </div>
                </div>
            ))}
        </div>
    </div>
)}

    
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
        "Regenerate Day 2", or "Keep budget under ₹30000"
    </p>
</div>
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
                onSelect={
                  setSelectedPlace
                }
                onRegenerate={handleRegenerateDay}
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

                <h4>Activities</h4>

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

                <h4>Food</h4>

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
          <h2 className="section-title">
            Trip Expenses
          </h2>

          <ExpenseCard
            total={expenseData.expenses.reduce(
              (sum, expense) =>
                sum + expense.amount,
              0
            )}
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

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginTop: 30,
        }}
      >
        <button
          className="download-button"
          onClick={() => {
            const tripId =
              getTripIdFromUrl();

            if (!tripId) return;

            window.open(
              `http://127.0.0.1:8000/trip/${tripId}/pdf`
            );
          }}
        >
          Download PDF
        </button>
      </div>
    </div>
  );
}