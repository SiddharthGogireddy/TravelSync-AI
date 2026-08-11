

export interface Summary {
    days: number;
    distance_km: number;
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

export interface Traveler {
    name: string;
    interests: string[];
    budget: string;
    pace: string;
}

export interface MandatoryVisit {
    name: string;
    day?: number;
}

export interface TripRequest {
    source: string;
    destination: string;
    days: number;

    travelers: Traveler[];

    mandatory_visits: MandatoryVisit[];

    travel_mode: "car" | "bus" | "train" | "flight";
}



export interface Itinerary {
    itinerary: string;
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
export interface BestTime {
    best_days: string[];
    reason: string;
}