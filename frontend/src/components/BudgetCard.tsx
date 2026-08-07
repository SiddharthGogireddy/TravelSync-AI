import type { Budget } from "../types/trip";
import ProgressBar from "./ProgressBar";
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

        <h2>Budget Summary</h2>

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
        Estimated :
        ₹{budget.estimated_cost}

        </h3>

        <h3>

        Remaining :
        ₹{budget.remaining}

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