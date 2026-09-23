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
import MapBounds from "./MapBounds";
import { useState } from "react";

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
const hotelIcon = new Icon({
    iconUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
});
const selectedIcon = new Icon({
    iconUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
});
const sourceIcon = new Icon({
    iconUrl:
        "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
});

const destinationIcon = new Icon({
    iconUrl:
        "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
});
export default function MapView({
    lat,
    lon,
    places,
    hotels,
    selectedPlace,
    routeCoordinates
}: Props) 
{   const [showFullRoute, setShowFullRoute] = useState(true); 
    const center: LatLngExpression = selectedPlace
    ? [selectedPlace.lat, selectedPlace.lon]
    : [lat, lon];
    return (
        <div className="map-wrapper">

        
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
    />  <MapBounds routeCoordinates={routeCoordinates} 
    fitRoute={showFullRoute}
/><button
    onClick={() => setShowFullRoute(true)}
    style={{
        position: "relative",
        height: "400px",
        width: "100%",
        top: "10px",
        right: "10px",
        zIndex: 1000,
        padding: "8px 12px",
        border: "none",
        borderRadius: "6px",
        background: "white",
        cursor: "pointer",
        boxShadow: "0 2px 6px rgba(0,0,0,0.2)"
    }}
>
    Show Full Route
</button>
            <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
      {routeCoordinates.length > 0 && (
    <>
        <Marker
            position={[
                routeCoordinates[0][0],
                routeCoordinates[0][1]
            ]}
            icon={sourceIcon}
        >
            <Popup>
                <strong>Source</strong>
            </Popup>
        </Marker>

        <Marker
            position={[
                routeCoordinates[routeCoordinates.length - 1][0],
                routeCoordinates[routeCoordinates.length - 1][1]
            ]}
            icon={destinationIcon}
        >
            <Popup>
                <strong>Destination</strong>
            </Popup>
        </Marker>
    </>
)}

<Marker position={[lat, lon]} icon={destinationIcon}>
    <Popup>
        <strong>Destination</strong>
    </Popup>
</Marker>
              <Polyline
    positions={routeCoordinates as [number,number][]}
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
> 
                
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
        icon={hotelIcon}
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
        <div className="map-legend">
        <div><span className="legend-dot source"></span> Source</div>
        <div><span className="legend-dot destination"></span> Destination</div>
        <div><span className="legend-dot attraction"></span> Attraction</div>
        <div><span className="legend-dot hotel"></span> Hotel</div>
    </div>
        </div>
    );
}