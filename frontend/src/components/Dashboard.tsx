import type { Dashboard as Dashboard } from "../types/trip";
import "../styles/card.css";
interface Props {
    dashboard: Dashboard;
}

export default function Dashboard({ dashboard }: Props) {
    return (
        <div className="dashboard">
           
              
    <div className="card">

    <h2>Trip Dashboard</h2>

    <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, 1fr)",
        gap: "10px"
    }}>

        <div>📍 {dashboard.source} → {dashboard.destination}</div>
        <div>📅 {dashboard.days} Days</div>
        <div>🚗 {dashboard.travel_mode}</div>
        <div>🏨 {dashboard.hotel_count} Hotels</div>
        <div>📍 {dashboard.attraction_count} Attractions</div>
        <div>⭐ {dashboard.mandatory_count} Mandatory</div>
        <div>🛣 {dashboard.distance} km</div>
        <div>⏱ {dashboard.duration} hrs</div>
        <div>💰 ₹{dashboard.budget}</div>

    </div>

</div> 
            

        </div>
    );
}