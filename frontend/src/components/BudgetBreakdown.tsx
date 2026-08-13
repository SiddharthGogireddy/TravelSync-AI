type Props = {
  categories: {
    hotel: number;
    food: number;
    transport: number;
    activities: number;
    emergency: number;
  };
};

export default function BudgetBreakdown({ categories }: Props) {
  return (
    <div className="card">
      <h2>Budget Breakdown</h2>

      <ul>
        <li> Hotel : ₹{categories.hotel.toLocaleString()}</li>
        <li> Food : ₹{categories.food.toLocaleString()}</li>
        <li> Transport : ₹{categories.transport.toLocaleString()}</li>
        <li> Activities : ₹{categories.activities.toLocaleString()}</li>
        <li> Emergency : ₹{categories.emergency.toLocaleString()}</li>
      </ul>
    </div>
  );
}