import type{ Summary } from "../types/api";
interface Props {
    summary: Summary;
}

export default function SummaryCard({ summary }: Props) {

    return (

        <div className="card">

            <h2>Trip Summary</h2>

            <p>Days: {summary.days}</p>

            <p>Distance: {summary.distance_km} km</p>

            <p>Travel Time: {summary.travel_time} hrs</p>

            <p>Hotels: {summary.hotel_count}</p>

            <p>Places: {summary.place_count}</p>

        </div>

    );

}