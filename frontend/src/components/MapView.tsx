import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { Station, Piste } from "../types";
import { enable3D, disable3D } from "../utils/map3D";
import { renderPistesLayer } from "../utils/pistesLayer";

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN as string;

type Props = {
  stations: Station[];
  setStations: (s: Station[]) => void;
  pistes: Piste[];
  setPistes: (p: Piste[]) => void;
  selectedStation: Station | null;
  setSelectedStation: (s: Station | null) => void;
  is3D: boolean;
};

export default function MapView({
  stations,
  setStations,
  pistes,
  setPistes,
  selectedStation,
  setSelectedStation,
  is3D,
}: Props) {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Init map
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [6.869, 45.923],
      zoom: 13,
    });

    mapRef.current = map;

    map.on("load", () => {
      if (is3D) enable3D(map);
    });

    return () => map.remove();
  }, []);

  // Fetch stations
  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/api/stations`)
      .then((r) => r.json())
      .then(setStations)
      .catch(console.error);
  }, []);

  // Add markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    stations.forEach((station) => {
      const coord = station.geometry?.coordinates ?? [station.longitude, station.latitude];
      const marker = new mapboxgl.Marker()
        .setLngLat(coord)
        .setPopup(new mapboxgl.Popup().setText(station.nom))
        .addTo(map);

      marker.getElement().addEventListener("click", async () => {
        setSelectedStation(station);
        const pistesResp: Piste[] = await fetch(
          `${import.meta.env.VITE_API_URL}/api/pistes/?station_id=${station.id}`
        ).then((r) => r.json());

        const list = Array.isArray(pistesResp) ? pistesResp : [];
        setPistes(list);
        renderPistesLayer(map, list);
      });
    });
  }, [stations]);

  // Apply 3D toggle
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (map.isStyleLoaded()) {
      is3D ? enable3D(map) : disable3D(map);
    } else {
      map.once("load", () => {
        is3D ? enable3D(map) : disable3D(map);
      });
    }
  }, [is3D]);

  return <div ref={containerRef} className="map-container" />;
}
