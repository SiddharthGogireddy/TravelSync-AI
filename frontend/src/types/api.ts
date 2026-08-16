import type { Budget } from "./trip";
export interface Dashboard {
    source: string;
    destination: string;
    days: number;
    travel_mode: string;
    hotel_count: number;
    attraction_count: number;
    mandatory_count: number;
    distance: number;
    duration: number;
    budget: number;
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
        destination_location:Location ;
        weather: Weather[];
        hotels: Hotel[];
        travelers: Traveler[];
        places:Place[]
        budget: Budget;
        day_schedule: Record<string, Place[]> | null;
    };

    itinerary?: Itinerary;
}