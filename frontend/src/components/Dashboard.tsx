import type { Dashboard as DashboardType } from "../types/api";
import "../styles/card.css";

interface Props {
    dashboard: DashboardType;
}

export default function Dashboard({ dashboard }: Props) {
    return (
        <div className="dashboard">
            <div className="card">
                <h2>Trip Dashboard</h2>
                <p className="dashboard-updated">
    Trip plan generated successfully
</p>
                <div className="dashboard-grid">

    <div className="dashboard-item">
        <span>Route</span>
        <strong>
            {dashboard.source} → {dashboard.destination}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Duration</span>
        <strong>
            {dashboard.days} Days
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Travel Mode</span>
        <strong>
            {dashboard.travel_mode}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Hotels</span>
        <strong>
            {dashboard.hotel_count}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Attractions</span>
        <strong>
            {dashboard.attraction_count}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Mandatory Visits</span>
        <strong>
            {dashboard.mandatory_count}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Scheduled Activities</span>
        <strong>
            {dashboard.total_activities}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Activities / Day</span>
        <strong>
            {dashboard.activities_per_day}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Total Journey Distance</span>
        <strong>
            {dashboard.distance} km
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Total Journey Time</span>
        <strong>
            {dashboard.duration} hrs
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Total Budget</span>
        <strong>
            ₹{dashboard.budget.toLocaleString()}
        </strong>
    </div>

    <div className="dashboard-item">
        <span>Estimated Cost</span>
        <strong>
            ₹{dashboard.estimated_cost.toLocaleString()}
        </strong>
    </div>

</div>
            </div>
        </div>
    );
}