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

import { addExpense, getExpenses } from "../services/expense";

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
    
  const [selectedPlace, setSelectedPlace] =
    useState<Place | null>(null);

  const [data, setData] =
    useState<TripResponse | null>(null);

  const [expenseData, setExpenseData] =
    useState<ExpenseResponse | null>(null);

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
      <Dashboard dashboard={dashboard} />
        
      <div className="section">
        <h2 className="section-title">
          Budget Overview
        </h2>

        <BudgetCard budget={trip.budget} />

        <BudgetStatus
          status={trip.budget.status}
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
      </div>

      <div className="section card">
        <h2 className="section-title">
          Hotels
        </h2>

        {trip.hotels.map(
          (hotel, index) => (
            <div
              key={index}
              style={{
                marginBottom: 10,
              }}
            >
              <a
                href={`https://www.google.com/maps?q=${hotel.lat},${hotel.lon}`}
                target="_blank"
                rel="noreferrer"
              >
                {hotel.name}
              </a>
            </div>
          )
        )}
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