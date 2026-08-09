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

export interface Budget {
    total?: number;
    estimated?: number;
    hotel?: number;
    food?: number;
    transport?: number;
    activities?: number;
    emergency?: number;
}

export interface Weather {
    date: string;
    max_temp: number;
    min_temp: number;
    description?: string;
}

export interface Hotel {
    name: string;
    distance?: number;
}

export interface Place {
    name: string;
    type?: string;
    category?: string;
}

export interface Traveler {
    name: string;
    budget: number;
    interests: string[];
    pace: string;
}

export interface BestTime {
    recommendation: string;
    best_days?: string[];
}

export interface Summary {
    days?: number;
    distance?: number;
    travel_time?: number;
    hotel_count?: number;
    place_count?: number;
}

export interface TripApiResponse {
    dashboard: Dashboard;
    summary: Summary;
    trip: {
        budget: Budget;
        weather: Weather[];
        hotels: Hotel[];
        day_schedule: Record<string, Place[]>;
        travelers: Traveler[];
        best_time: BestTime;
    };
    itinerary: {
        itinerary: string;
    };
}