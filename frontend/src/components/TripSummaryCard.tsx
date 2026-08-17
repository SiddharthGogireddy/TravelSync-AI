interface Props {
    hotels: number;
    attractions: number;
    distance: number;
    duration: number;
}

export default function TripSummaryCard({
    hotels,
    attractions,
    distance,
    duration
}: Props) {
    return (
        <div
            style={{
                padding: "20px",
                border: "1px solid lightgray",
                borderRadius: "12px"
            }}
        >
            <h2>Trip Summary</h2>

            <p>🏨 Hotels: {hotels}</p>

            <p>📍 Attractions: {attractions}</p>

            <p>🚗 Distance: {distance} km</p>

            <p>⏱️ Duration: {duration} hrs</p>
        </div>
    );
}