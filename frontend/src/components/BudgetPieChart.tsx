import { useState, useEffect } from "react";
import {
    PieChart,
    Pie,
    Cell,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";

type Props = {
    categories?: {
        hotel?: number;
        food?: number;
        transport?: number;
        activities?: number;
        emergency?: number;
    };
};

const COLORS = [
    "#4F46E5", // Indigo (Hotel)
    "#06B6D4", // Cyan (Food)
    "#10B981", // Emerald (Transport)
    "#F59E0B", // Amber (Activities)
    "#EF4444", // Rose (Emergency)
    "#8B5CF6", // Purple
];

export default function BudgetPieChart({
    categories = {},
}: Props) {
    const [isWide, setIsWide] = useState(
        typeof window !== "undefined" ? window.innerWidth >= 640 : true
    );

    useEffect(() => {
        const handleResize = () => {
            setIsWide(window.innerWidth >= 640);
        };
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, []);

    const rawData = [
        {
            name: "Hotel",
            value: Math.max(0, Number(categories?.hotel || 0)),
        },
        {
            name: "Food",
            value: Math.max(0, Number(categories?.food || 0)),
        },
        {
            name: "Transport",
            value: Math.max(0, Number(categories?.transport || 0)),
        },
        {
            name: "Activities",
            value: Math.max(0, Number(categories?.activities || 0)),
        },
        {
            name: "Emergency",
            value: Math.max(0, Number(categories?.emergency || 0)),
        },
    ];

    const hasData = rawData.some((item) => item.value > 0);
    const data = hasData ? rawData : rawData.map((d) => ({ ...d, value: 1 }));
    const total = rawData.reduce((sum, item) => sum + item.value, 0);

    const renderLegendItem = (value: string, entry: any) => {
        const itemVal = entry?.payload?.value ?? 0;
        const actualVal = hasData ? itemVal : 0;
        const pct = total > 0 ? Math.round((actualVal / total) * 100) : 0;

        return (
            <span
                style={{
                    color: "#334155",
                    fontSize: "0.85rem",
                    fontWeight: 500,
                    marginRight: isWide ? 0 : 12,
                    display: isWide ? "inline-block" : "inline",
                    lineHeight: isWide ? "1.8" : "1.4",
                }}
            >
                {value}: ₹{actualVal.toLocaleString()} {total > 0 ? `(${pct}%)` : ""}
            </span>
        );
    };

    return (
        <div
            style={{
                width: "100%",
                height: "auto",
                minHeight: isWide ? 380 : 420,
                background: "white",
                borderRadius: 12,
                padding: isWide ? "24px 24px" : "20px 16px",
                boxShadow: "0 2px 8px rgba(0,0,0,.08)",
                boxSizing: "border-box",
                marginBottom: 24,
                overflow: "hidden",
            }}
        >
            <h2
                style={{
                    margin: "0 0 16px 0",
                    fontSize: "1.25rem",
                    fontWeight: 600,
                    color: "#1e293b",
                }}
            >
                Budget Distribution
            </h2>

            <div
                style={{
                    width: "100%",
                    height: isWide ? 300 : 340,
                    position: "relative",
                }}
            >
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart
                        margin={{
                            top: 10,
                            right: isWide ? 20 : 10,
                            bottom: isWide ? 10 : 25,
                            left: 10,
                        }}
                    >
                        <Pie
                            data={data}
                            dataKey="value"
                            nameKey="name"
                            cx={isWide ? "40%" : "50%"}
                            cy={isWide ? "50%" : "40%"}
                            outerRadius={isWide ? 95 : 75}
                            innerRadius={isWide ? 48 : 36}
                            paddingAngle={3}
                        >
                            {data.map((_, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={COLORS[index % COLORS.length]}
                                />
                            ))}
                        </Pie>

                        <Tooltip
                            formatter={(val: any) => [
                                `₹${Number(hasData ? val : 0).toLocaleString()}`,
                                "Budget",
                            ]}
                            contentStyle={{
                                backgroundColor: "white",
                                borderRadius: 8,
                                border: "1px solid #e2e8f0",
                                boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                                fontSize: "0.85rem",
                            }}
                        />

                        <Legend
                            layout={isWide ? "vertical" : "horizontal"}
                            align={isWide ? "right" : "center"}
                            verticalAlign={isWide ? "middle" : "bottom"}
                            iconType="circle"
                            iconSize={8}
                            wrapperStyle={
                                isWide
                                    ? {
                                          paddingLeft: 20,
                                          lineHeight: "28px",
                                      }
                                    : {
                                          paddingTop: 16,
                                          textAlign: "center",
                                          width: "100%",
                                      }
                            }
                            formatter={renderLegendItem}
                        />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}