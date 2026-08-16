import type { LatLngExpression } from "leaflet";
import type { Place ,Hotel} from "../types/api"
import {
    MapContainer,
    TileLayer,
    Marker,
    Popup,
    
} from "react-leaflet";

import "leaflet/dist/leaflet.css";


interface Props {
    lat: number;
    lon: number;
    places: Place[];
    hotels: Hotel[];
    selectedPlace: Place | null;
}

export default function MapView({
    lat,
    lon,
    places,
    selectedPlace
}: Props) 
{    const center: LatLngExpression = selectedPlace
    ? [selectedPlace.lat, selectedPlace.lon]
    : [lat, lon];
    return (
        <MapContainer
            center={center}
            zoom={12}
            style={{
                height: "500px",
                width: "100%"
            }}
        >
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {places.map((place, index) => (
                <Marker
                    key={index}
                    position={[
                        place.lat,
                        place.lon
                    ]}
                >
                    <Popup>
                        {place.name}
                    </Popup>
                </Marker>
            ))}
        </MapContainer>
    );
}