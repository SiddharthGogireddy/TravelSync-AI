type Props = {
  status: string;
};

export default function BudgetStatus({ status }: Props) {
  let color = "#4caf50";

  if (status === "Near Budget") color = "#ff9800";

  if (status === "Over Budget") color = "#f44336";

  return (
    <div
      style={{
        background: color,
        color: "white",
        padding: "12px",
        borderRadius: "8px",
        textAlign: "center",
        fontWeight: "bold",
      }}
    >
      {status}
    </div>
  );
}