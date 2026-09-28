import type { LatLngExpression } from "leaflet";
import { Icon } from "leaflet";
import type { Place, Hotel } from "../types/api";

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
    routeCoordinates: [number, number][];
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
    popupAnchor: [1, -34]
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
    popupAnchor: [1, -34]
});

const destinationIcon = new Icon({
    iconUrl:
        "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
    shadowUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34]
});

export default function MapView({
    lat,
    lon,
    places,
    hotels,
    selectedPlace,
    routeCoordinates
}: Props) {
    const center: LatLngExpression = selectedPlace
        ? [selectedPlace.lat, selectedPlace.lon]
        : [lat, lon];

    const validRoute =
        routeCoordinates &&
        routeCoordinates.length > 0 &&
        routeCoordinates.every(
            (point) =>
                Array.isArray(point) &&
                point.length >= 2 &&
                point[0] != null &&
                point[1] != null
        );

    return (
        <div
            className="map-wrapper"
            style={{ position: "relative" }}
        >
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

                {/* Route + Source/Destination */}

                {validRoute && (
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
                                routeCoordinates[
                                    routeCoordinates.length - 1
                                ][0],
                                routeCoordinates[
                                    routeCoordinates.length - 1
                                ][1]
                            ]}
                            icon={destinationIcon}
                        >
                            <Popup>
                                <strong>Destination</strong>
                            </Popup>
                        </Marker>

                        <Polyline
                            positions={routeCoordinates}
                        />
                    </>
                )}

                {/* Destination marker */}

                <Marker
                    position={[lat, lon]}
                    icon={destinationIcon}
                >
                    <Popup>
                        <strong>Destination</strong>
                    </Popup>
                </Marker>

                {/* Attractions */}

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

                {/* Hotels */}

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

            {/* Map Legend */}

            <div className="map-legend">
                <div>
                    <span className="legend-dot source"></span>
                    Source
                </div>

                <div>
                    <span className="legend-dot destination"></span>
                    Destination
                </div>

                <div>
                    <span className="legend-dot attraction"></span>
                    Attraction
                </div>

                <div>
                    <span className="legend-dot hotel"></span>
                    Hotel
                </div>
            </div>
        </div>
    );
}