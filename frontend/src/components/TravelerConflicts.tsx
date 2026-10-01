import type { TravelerConflict } from "../types/api";

interface Props {
    conflicts: TravelerConflict[];
}

export default function TravelerConflicts({ conflicts }: Props) {
    if (!conflicts || conflicts.length === 0) {
        return null;
    }

    return (
        <div className="section">
            <h2 className="section-title">
                Traveler Preferences
            </h2>

            {conflicts.map((conflict, index) => (
                <div
                    key={`${conflict.type}-${conflict.interest ?? ""}-${index}`}
                    style={{
                        padding: "12px 16px",
                        marginBottom: "10px",
                        borderRadius: "8px",
                        border: "1px solid #ddd",
                    }}
                >
                    <strong>
                        {conflict.type === "pace"
                            ? "Different Travel Paces"
                            : `Interest: ${conflict.interest}`}
                    </strong>

                    <p>{conflict.message}</p>

                    <small>
                        Travelers: {conflict.travelers.join(", ")}
                    </small>
                </div>
            ))}
        </div>
    );
}