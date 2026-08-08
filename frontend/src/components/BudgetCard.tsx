import type { Budget } from "../types/trip";
import ProgressBar from "./ProgressBar";
import "../styles/card.css";
interface Props{

    budget:Budget;
    
}

export default function BudgetCard({

    budget,

}:Props){
    const max = Math.max(
    budget.categories.hotel,
    budget.categories.food,
    budget.categories.transport,
    budget.categories.activities,
    budget.categories.emergency
);
    return(

        <div
        style={{
            border:"1px solid #ddd",
            padding:20,
            marginBottom:20,
            borderRadius:10
        }}
        >
            <h2 style={{ marginBottom: 10 }}>Budget Summary</h2>

<div style={{ fontSize: 18, fontWeight: "bold" }}>
    ₹{budget.estimated_cost}
</div>

<div style={{ color: "green" }}>
    Remaining: ₹{budget.remaining}
</div>
        <h2 style={{ marginBottom: 10 }}>Budget Summary</h2>
        <div className="card"></div>
        <p>
            Hotel :
            ₹{budget.categories.hotel}
        </p>
        
        <p>
            Food :
            ₹{budget.categories.food}
        </p>

        <p>
            Transport :
            ₹{budget.categories.transport}
        </p>

        <p>
            Activities :
            ₹{budget.categories.activities}
        </p>

        <p>
            Emergency :
            ₹{budget.categories.emergency}
        </p>

        <hr/>

        <h3>
        <ProgressBar
    label="Hotel"
    value={budget.categories.hotel}
    max={max}
/>

<ProgressBar
    label="Food"
    value={budget.categories.food}
    max={max}
/>

<ProgressBar
    label="Transport"
    value={budget.categories.transport}
    max={max}
/>

<ProgressBar
    label="Activities"
    value={budget.categories.activities}
    max={max}
/>

<ProgressBar
    label="Emergency"
    value={budget.categories.emergency}
    max={max}
/>
        <div style={{ fontSize: 18, fontWeight: "bold" }}>
    ₹{budget.estimated_cost}
</div>

        </h3>

        <h3>

        <div style={{ color: "green" }}>
    Remaining: ₹{budget.remaining}
</div>

        </h3>

        <h3>

        Per Person

        </h3>

        {

            budget.per_person.map(person=>(

                <div key={person.name}>

                    <strong>

                    {person.name}

                    </strong>

                    ₹{person.share}

                </div>

            ))

        }

        </div>

    );

}