import type { Budget } from "./trip";
import type { Transport } from "./trip";
export interface Dashboard {
    source: string;
    destination: string;
    days: number;
    travel_mode: string;

    weather: string;

    hotel_count: number;
    attraction_count: number;
    mandatory_count: number;

    total_activities: number;
    activities_per_day: number;

    distance: number;
    duration: number;

    budget: number;
    estimated_cost: number;
    remaining: number;
    budget_status: string;

    hotel_cost: number;
    food_cost: number;
    transport_cost: number;
    activity_cost: number;
    emergency_cost: number;

    average_per_day: number;
    average_per_person: number;
}

export interface Summary {
    days: number;
    distance_km: number;
    travel_time: number;
    hotel_count: number;
    place_count: number;
}

export interface BudgetCategory {
    hotel: number;
    food: number;
    transport: number;
    activities: number;
    emergency: number;
}

export interface BudgetPerson {
    name: string;
    share: number;
}

export interface Location {
    lat: number;
    lon: number;
}

export interface Weather {
    date: string;
    max_temp: number;
    min_temp: number;
    weather_code?: number;
    description?: string;
}

export interface Hotel {
    name: string;
    distance_km: number;
    lat:number;
    lon:number;
}

export interface Place {
    name: string;
    category: string;
    distance_km: number;
    lat: number;
    lon: number;
    score?: number;
    matched_travelers?: string[];
    match_count?: number;
    travel_from_previous_km?: number | null;
}
export interface ItineraryDay {
    day: number;
    title: string;
    activities: string[];
    food: string[];
    budget: string;
}

export interface Itinerary {
    days: ItineraryDay[];
}
export interface Traveler {
    name: string;
    budget: string;
    interests: string[];
    pace: string;
}

export interface BestTime {
    best_days: string[];
    reason: string;
}

export interface TripResponse {
    trip_id: string;

    dashboard: Dashboard;

    summary: Summary;

    trip: {
        destination_location: Location;
        weather: Weather[];
        hotels: Hotel[];
        travelers: Traveler[];
        places: Place[];
        budget: Budget;

        day_schedule: Record<
            string,
            Place[]
        > | null;

        transport: Transport;
    };

    itinerary?: Itinerary;
}
