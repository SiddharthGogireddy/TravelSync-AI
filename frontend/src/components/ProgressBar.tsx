
interface Props {
    label: string;
    value: number;
    max: number;
}

export default function ProgressBar({
    label,
    value,
    max,
}: Props) {

    const width = max === 0 ? 0 : (value / max) * 100;

    return (
        <div style={{ marginBottom: 15 }}>

            <strong>{label}</strong>

            <div
                style={{
                    background: "#ddd",
                    height: 12,
                    borderRadius: 6,
                    overflow: "hidden",
                    marginTop: 5,
                }}
            >
                <div
                    style={{
                        width: `${width}%`,
                        background: "#4caf50",
                        height: "100%",
                    }}
                />
            </div>

            <small>₹{value}</small>

        </div>
    );
}