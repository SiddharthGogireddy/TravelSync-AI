import type { LatLngExpression } from "leaflet";
import { Icon } from "leaflet";
import type { Place ,Hotel} from "../types/api"
import {
    MapContainer,
    TileLayer,
    Marker,
    Popup,
    Polyline
    
} from "react-leaflet";
import MapUpdater from "./MapUpdater";
import "leaflet/dist/leaflet.css";


interface Props {
    lat: number;
    lon: number;
    places: Place[];
    hotels: Hotel[];
    selectedPlace: Place | null;
    routeCoordinates: number[][];
}
const defaultIcon = new Icon({
    iconUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
});

const selectedIcon = new Icon({
    iconUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
});
export default function MapView({
    lat,
    lon,
    places,
    hotels,
    selectedPlace,
    routeCoordinates
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
            <MapUpdater
        selectedPlace={selectedPlace}
    />  
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {places.map((place, index) => (
                <Marker
                    
    key={`place-${index}`}
    position={[
        place.lat,
        place.lon
    ]}
    icon={
        selectedPlace?.name === place.name
            ? selectedIcon
            : defaultIcon
    }
>   <Polyline
    positions={routeCoordinates as [number,number][]}
/>
                
                    <Popup> 
    <div>
        <h3>{place.name}</h3>

        <p>
            {place.category}
        </p>

        <p>
            {place.distance_km} km away
        </p>
    </div>
</Popup>
                </Marker>
                
            ))}
            {hotels.map((hotel, index) => (
    <Marker
        key={`hotel-${index}`}
        position={[
            hotel.lat,
            hotel.lon
        ]}
    >
        <Popup>
            <div>
                <h3>{hotel.name}</h3>

                <p>Hotel</p>

                <p>
                    {hotel.distance_km} km away
                </p>
            </div>
        </Popup>
    </Marker>
))}
        </MapContainer>
    );
}