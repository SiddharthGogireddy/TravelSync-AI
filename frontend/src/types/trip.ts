export interface Summary {
    days: number;
    distance: number;
    travel_time: number;
    hotel_count: number;
    place_count: number;
}

export interface Hotel {
    name: string;
    distance_km: number;
}

export interface Weather {
    date: string;
    description: string;
    min_temp: number;
    max_temp: number;
}

export interface Place {
    name: string;
    category: string;
}

export interface Trip {
    weather: Weather[];
    hotels: Hotel[];
    day_schedule: Record<string, Place[]>;
}

export interface Itinerary {
    itinerary: string;
}

export interface PlannerResponse {
    summary: Summary;
    trip: Trip;
    itinerary: Itinerary;
}