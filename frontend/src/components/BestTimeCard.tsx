import type { BestTime } from "../types/api";

export default function BestTimeCard({ data }: { data: BestTime }) {
    return (
        <div className="card">
            <h3>Best Days to Visit</h3>

            <div>
                {data.best_days.map((d) => (
                    <span key={d} style={{ marginRight: 10 }}>
                        {d}
                    </span>
                ))}
            </div>

            <p>{data.reason}</p>
        </div>
    );
} 