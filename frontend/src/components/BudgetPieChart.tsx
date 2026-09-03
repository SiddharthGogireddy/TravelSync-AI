import {
    PieChart,
    Pie,
    Cell,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";

type Props = {
    categories: {
        hotel: number;
        food: number;
        transport: number;
        activities: number;
        emergency: number;
    };
};

const COLORS = [
    "#0088FE",
    "#00C49F",
    "#FFBB28",
    "#FF8042",
    "#AA66CC",
];

export default function BudgetPieChart({
    categories,
}: Props) {

    const data = [
        {
            name: "Hotel",
            value: categories.hotel,
        },
        {
            name: "Food",
            value: categories.food,
        },
        {
            name: "Transport",
            value: categories.transport,
        },
        {
            name: "Activities",
            value: categories.activities,
        },
        {
            name: "Emergency",
            value: categories.emergency,
        },
    ];

    return (
        <div
            style={{
                width: "100%",
                height: 400,
                background: "white",
                borderRadius: 12,
                padding: 20,
                boxShadow:
                    "0 2px 8px rgba(0,0,0,.15)",
            }}
        >
            <h2>Budget Distribution</h2>
            <ResponsiveContainer>
    
    <PieChart>
        <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            outerRadius={120}
            label
        >
            {data.map((_, index) => (
                <Cell
                    key={index}
                    fill={
                        COLORS[
                            index % COLORS.length
                        ]
                    }
                />
            ))}
        </Pie>

        <Tooltip />

        <Legend
    wrapperStyle={{
        paddingTop: "20px",
    }}
/>
    </PieChart>
</ResponsiveContainer>
        </div>
    );
}