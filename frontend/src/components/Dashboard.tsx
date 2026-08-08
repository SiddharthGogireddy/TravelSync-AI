import type { Dashboard as DashboardType } from "../types/trip";

interface Props {
    dashboard: DashboardType;
}

export default function Dashboard({ dashboard }: Props) {
    return (
        <div className="dashboard">

            <h2>Trip Dashboard</h2>

            <p>
                 {dashboard.source} → {dashboard.destination}
            </p>

            <p> {dashboard.days} Days</p>

            <p> {dashboard.travel_mode}</p>

            <p> {dashboard.hotel_count} Hotels</p>

            <p> {dashboard.attraction_count} Attractions</p>

            <p> {dashboard.mandatory_count} Mandatory Stops</p>

            <p> {dashboard.distance} km</p>

            <p> {dashboard.duration} hrs</p>

            <p> ₹{dashboard.budget}</p>

        </div>
    );
}