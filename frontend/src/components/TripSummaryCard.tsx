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

            <p>Hotels: {hotels}</p>

            <p>Attractions: {attractions}</p>

            <p>Distance: {distance > 0 ? `${distance} km` : "N/A"}</p>

            <p>Duration: {duration > 0 ? `${duration} hrs` : "N/A"}</p>
        </div>
    );
}