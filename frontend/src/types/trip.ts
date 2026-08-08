export interface Summary {
    days: number;
    distance: number;
    travel_time: number;
    hotel_count: number;
    place_count: number;
}
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
export interface Hotel {
    name: string;
    distance_km: number;
}
export interface TripRequest {
    source: string;
    destination: string;
    days: number;

    travelers: {
        name: string;
        interests: string[];
        budget: string;
        pace: string;
    }[];

    mandatory_visits: {
        name: string;
        day: number;
    }[];
    travel_mode: string;
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
    budget: Budget;
}

export interface Itinerary {
    itinerary: string;
}

export interface PlannerResponse {
    summary: Summary;
    trip: Trip;
    itinerary: Itinerary;
}
export interface BudgetCategory {

    hotel:number;
    food:number;
    transport:number;
    activities:number;
    emergency:number;

}

export interface BudgetPerson{

    name:string;
    share:number;

}

export interface Budget{

    total_budget:number;
    estimated_cost:number;
    remaining:number;

    categories:BudgetCategory;

    per_person:BudgetPerson[];

}