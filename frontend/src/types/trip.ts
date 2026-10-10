
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

    total?: number;
    currency?: string;
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
export interface TransportLeg {
    type: string;
    mode: string;
    label: string;
    from: string;
    to: string;
    distance_km: number;
    duration_hours: number;
}

export interface Transport {
    mode: string;
    label: string;
    description: string;
    source: string;
    destination: string;

    distance_km: number;
    duration_hours: number;

    legs: TransportLeg[];
}

export interface DestinationStop {
    name: string;
    days: number;
}

export interface InterDestinationTravelLeg {
    leg_index: number;
    from_location: string;
    to_location: string;
    distance_km: number;
    duration_hours: number;
    travel_mode: string;
    departure_day: number;
}

export interface DestinationSummary {
    stop_index: number;
    name: string;
    days: number;
    start_day: number;
    end_day: number;
    location?: { lat: number; lon: number };
    attraction_count?: number;
    hotel_count?: number;
}

export interface PlanningConstraints {
    max_daily_distance_km?: number;
    max_budget?: number;
    min_attractions_per_day?: number;
    preferred_travel_mode?: string;
    must_visit_locations?: string[];
    locations_to_avoid?: string[];
}

export interface ConstraintAnalysis {
    all_satisfied: boolean;
    satisfied_constraints: string[];
    unsatisfied_constraints: string[];
    explanations: string[];
    conflicts_detected: string[];
    daily_distance_audit: Record<string, number>;
}

export interface TripRequest {
    source: string;
    destination: string;
    days: number;
    destinations?: DestinationStop[];
    travel_mode: string;
    travelers: TravelerRequest[];
    mandatory_visits: MandatoryVisit[];
    constraints?: PlanningConstraints;
}

export interface MealItem {
    meal_type: string;
    time_slot: string;
    name: string;
    cuisine: string;
    distance_km: number;
    estimated_cost_per_person: number;
    price_tier: string;
    dietary_tags: string[];
    near_location?: string;
}

export interface RestBreakItem {
    break_type: string;
    time_slot: string;
    duration_minutes: number;
    recommended_activity: string;
    reason: string;
    location_context: string;
}

export interface DayMealsAndBreaks {
    day: number;
    meals: MealItem[];
    rest_breaks: RestBreakItem[];
    total_estimated_meal_cost: number;
}
