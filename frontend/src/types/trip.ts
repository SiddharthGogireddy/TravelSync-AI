
export interface BudgetCategory {
    hotel: number;
    food: number;
    transport: number;
    activities: number;
    emergency: number;
}

export interface CategoryPercentage {
    hotel: number;
    food: number;
    transport: number;
    activities: number;
    emergency: number;
}

export interface PerPersonBudget {
    name: string;
    share: number;
}

export interface Budget {
    total_budget: number;
    estimated_cost: number;
    remaining: number;

    status: string;

    average_per_day: number;

    average_per_person: number;

    categories: BudgetCategory;

    category_percentage: CategoryPercentage;

    per_person: PerPersonBudget[];
}
export interface TravelerRequest {
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
    travel_mode: string;
    travelers: TravelerRequest[];
    mandatory_visits: MandatoryVisit[];
}