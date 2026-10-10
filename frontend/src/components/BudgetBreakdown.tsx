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
  const safeCategories = {
    hotel: categories?.hotel ?? 0,
    food: categories?.food ?? 0,
    transport: categories?.transport ?? 0,
    activities: categories?.activities ?? 0,
    emergency: categories?.emergency ?? 0,
  };

  return (
    <div className="card">
      <h2>Budget Breakdown</h2>

      <ul>
        <li> Hotel : ₹{safeCategories.hotel.toLocaleString()}</li>
        <li> Food : ₹{safeCategories.food.toLocaleString()}</li>
        <li> Transport : ₹{safeCategories.transport.toLocaleString()}</li>
        <li> Activities : ₹{safeCategories.activities.toLocaleString()}</li>
        <li> Emergency : ₹{safeCategories.emergency.toLocaleString()}</li>
      </ul>
    </div>
  );
}