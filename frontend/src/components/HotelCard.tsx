import type{ Hotel } from "../types/trip";


interface Props {
    hotel: Hotel;
}

export default function HotelCard({ hotel }: Props) {

    return (

        <div className="card">

            <h3>{hotel.name}</h3>

            <p>{hotel.distance_km} km away</p>

        </div>

    );

}