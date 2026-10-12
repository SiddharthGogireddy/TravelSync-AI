import { API } from "./api";

export interface DailyForecast {
  day: number;
  date: string;
  destination: string;
  status: "available" | "beyond_horizon" | "past_date" | "unavailable";
  weather_code?: number;
  condition: string;
  icon: string;
  category?: string;
  min_temp?: number | null;
  max_temp?: number | null;
  precipitation_probability?: number | null;
  precipitation_sum?: number | null;
  wind_speed_max?: number | null;
  message?: string;
  update_time?: string;
  provider?: string;
}

export interface WeatherDisruptionAlert {
  day: number;
  date: string;
  destination: string;
  warning_source: "travelsync_ai" | "official_provider";
  alert_type: "advisory" | "warning" | "severe";
  severity: "low" | "medium" | "high";
  title: string;
  message: string;
  affected_outdoor_activities: string[];
  recommendation: string;
}

export interface TripWeatherAlertsResponse {
  success: boolean;
  trip_id: string;
  destination: string;
  is_multi_destination: boolean;
  has_explicit_dates: boolean;
  base_date: string;
  forecast_horizon_days: number;
  daily_forecasts: DailyForecast[];
  disruption_alerts: WeatherDisruptionAlert[];
  alert_count: number;
  update_time: string;
  disclaimer: string;
}

export async function getTripWeatherAlerts(tripId: string): Promise<TripWeatherAlertsResponse> {
  const res = await fetch(`${API}/weather/trip/${encodeURIComponent(tripId)}/alerts`);
  if (!res.ok) {
    throw new Error(`Failed to fetch weather alerts for trip (${res.status})`);
  }
  return res.json();
}

export async function getLocationForecast(lat: number, lon: number, days = 7): Promise<any> {
  const res = await fetch(`${API}/weather/forecast?lat=${lat}&lon=${lon}&days=${days}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch location forecast (${res.status})`);
  }
  return res.json();
}
