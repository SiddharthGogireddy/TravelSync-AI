export interface TemplatePlaceSummary {
  name: string;
  category: string;
  duration_hours: number;
}

export interface TemplateStructure {
  days_count: number;
  places_count: number;
  hotels_count: number;
  mandatory_visits?: string[];
  places_summary: TemplatePlaceSummary[];
  schedule_outline: Record<string, number>;
}

export interface TripTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  source_trip_id?: string;
  created_at: string;
  destination: string;
  source: string;
  duration_days: number;
  travel_mode: string;
  preferences: string[];
  budget_summary?: {
    total_budget: number;
    estimated_cost: number;
  };
  route_summary?: {
    distance_km: number;
    duration_hr: string | number;
  };
  itinerary_structure: TemplateStructure;
  template_data?: any;
}
