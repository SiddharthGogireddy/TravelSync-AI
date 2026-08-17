import { useMap } from "react-leaflet";
import { useEffect } from "react";

import type { Place } from "../types/api";

interface Props {
    selectedPlace: Place | null;
}

export default function MapUpdater({
    selectedPlace
}: Props) {
    const map = useMap();

    useEffect(() => {
        if (!selectedPlace) {
            return;
        }

        map.flyTo(
            [
                selectedPlace.lat,
                selectedPlace.lon
            ],
            15
        );
    }, [selectedPlace, map]);

    return null;
}