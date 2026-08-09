import type { Weather } from "../types/api";


interface Props {
    weather: Weather;
}

export default function WeatherCard({ weather }: Props) {

    return (

        <div className="card">

            <h3>{weather.date}</h3>

            <p>{weather.description}</p>

            <p>

                {weather.min_temp}°C - {weather.max_temp}°C

            </p>

        </div>

    );

}