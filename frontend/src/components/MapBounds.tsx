import { useEffect } from "react";
import { useMap } from "react-leaflet";

interface Props {
    routeCoordinates?: [number, number][];
    fitRoute: boolean;
}

export default function MapBounds({
    routeCoordinates = [],
    fitRoute
}: Props) {
    const map = useMap();

    useEffect(() => {
        if (!fitRoute || routeCoordinates.length === 0) {
            return;
        }

        const bounds = routeCoordinates.map(
            ([lat, lon]) => [lat, lon] as [number, number]
        );

        map.fitBounds(bounds, {
            padding: [30, 30]
        });
    }, [map, routeCoordinates, fitRoute]);

    return null;
}