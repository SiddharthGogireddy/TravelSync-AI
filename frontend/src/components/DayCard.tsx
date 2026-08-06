import type { Place } from "../types/trip";
interface Props {

    day: string;

    places: Place[];

}

export default function DayCard({ day, places }: Props) {

    return (

        <div className="card">

            <h2>Day {day}</h2>

            <ul>

                {places.map((place, index) => (

                    <li key={index}>

                        {place.name}

                        {" - "}

                        {place.category}

                    </li>

                ))}

            </ul>

        </div>

    );

}