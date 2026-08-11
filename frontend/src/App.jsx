import { useState } from "react";
import { generateItinerary } from "./services/api";

function App() {
  const [form, setForm] = useState({
    destination: "",
    days: 3,
    budget: 50000,
    travelers: 2,
    interests: "",
  });

  const [itinerary, setItinerary] = useState(null);

  const handleSubmit = async () => {
    const data = {
      ...form,
      interests: form.interests.split(","),
    };

    const res = await generateItinerary(data);
    setItinerary(res);
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>TravelSync AI ✈️</h1>

      {/* FORM */}
      <input
        placeholder="Destination"
        onChange={(e) => setForm({ ...form, destination: e.target.value })}
      />

      <input
        placeholder="Days"
        type="number"
        onChange={(e) => setForm({ ...form, days: +e.target.value })}
      />

      <input
        placeholder="Budget"
        type="number"
        onChange={(e) => setForm({ ...form, budget: +e.target.value })}
      />

      <input
        placeholder="Interests (comma separated)"
        onChange={(e) => setForm({ ...form, interests: e.target.value })}
      />

      <button onClick={handleSubmit}>Generate</button>

      {/* OUTPUT */}
      {itinerary?.days?.map((day) => (
        <div key={day.day} style={{ border: "1px solid #ccc", margin: "10px", padding: "10px" }}>
          <h2>Day {day.day}: {day.title}</h2>

          <h4>Activities:</h4>
          <ul>
            {day.activities.map((a, i) => <li key={i}>{a}</li>)}
          </ul>

          <h4>Food:</h4>
          <ul>
            {day.food.map((f, i) => <li key={i}>{f}</li>)}
          </ul>

          <p><strong>Budget:</strong> {day.budget}</p>
        </div>
      ))}
    </div>
  );
}

export default App;