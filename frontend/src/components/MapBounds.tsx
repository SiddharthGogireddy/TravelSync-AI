import { useEffect } from "react";
import { useMap } from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";

interface Props {
    routeCoordinates: number[][];
    fitRoute: boolean;
}

export default function MapBounds({
    routeCoordinates,
    fitRoute
}: Props) {
    const map = useMap();

    useEffect(() => {
        if (!fitRoute || !routeCoordinates.length) return;

        const bounds: LatLngBoundsExpression = routeCoordinates.map(
            ([lat, lon]) => [lat, lon] as [number, number]
        );

        map.fitBounds(bounds, {
            padding: [30, 30]
        });
    }, [map, routeCoordinates, fitRoute]);

    return null;
}