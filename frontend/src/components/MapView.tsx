import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
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
  isSatellite: boolean;
  targetPisteId: number | null;
  setTargetPisteId: (id: number | null) => void;
};

export type MapViewHandle = {
  resetBearing: () => void;
};

const MapView = forwardRef<MapViewHandle, Props>(({ 
  stations,
  setStations,
  pistes,
  setPistes,
  setSelectedStation,
  is3D,
  isSatellite,
  targetPisteId,
  setTargetPisteId,
}, ref) => {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Reset Bearing to north
  useImperativeHandle(ref, () => ({
    resetBearing: () => {
      const map = mapRef.current;
      if (!map) return;
      map.easeTo({ bearing: 0, duration: 800 });
    },
  }));

  // Init map
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [6.068348, 45.092624,],
      zoom: 13,
      bearing: 0,
    });

    mapRef.current = map;

    map.on("load", () => {
      if (is3D) enable3D(map);
    });

    return () => map.remove();
  }, []);

  // Toggle 3D
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

  // Toggle satellite style
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const style = isSatellite
      ? "mapbox://styles/mapbox/satellite-streets-v12"
      : "mapbox://styles/mapbox/streets-v12";

    // Sauvegarder l'état 3D avant le changement de style
    const was3D = is3D;

    // Appliquer le nouveau style
    map.setStyle(style);

    // Réappliquer la 3D et les pistes après le chargement du nouveau style
    const onStyleLoad = () => {
      if (was3D) {
        enable3D(map);
      }
      if (pistes.length > 0) {
        renderPistesLayer(map, pistes);
      }
      map.off("style.load", onStyleLoad);
    };

    map.on("style.load", onStyleLoad);
  }, [isSatellite]);

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
        // Zoom to station selected
        const target = station.geometry?.coordinates ?? [station.longitude, station.latitude];
        map.easeTo({ center: target as [number, number], zoom: 14, duration: 800 });
        // clear target piste to avoid re-zooming on previous selection
        setTargetPisteId(null);

        const pistesResp: Piste[] = await fetch(
          `${import.meta.env.VITE_API_URL}/api/pistes/?station_id=${station.id}`
        ).then((r) => r.json());
        const list = Array.isArray(pistesResp) ? pistesResp : [];
        setPistes(list);
        renderPistesLayer(map, list);
      });
    });
  }, [stations]);

  // Zoom to a piste when selected from sidebar
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (pistes.length === 0) return;
    if (typeof targetPisteId !== 'number') return;
    const piste = pistes.find(p => p.id === targetPisteId);
    if (!piste || !piste.geometry) return;
    const coords = piste.geometry.coordinates;
    if (!coords || coords.length === 0) return;
    const bounds = coords.reduce((b, [lng, lat]) => b.extend([lng, lat]), new mapboxgl.LngLatBounds(coords[0] as any, coords[0] as any));
    map.fitBounds(bounds, { padding: 40, maxZoom: 13, duration: 700 });
  }, [targetPisteId, pistes]);

  // Remove pistes layer when cleared from Topbar/state
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (pistes.length === 0) {
      if (map.getLayer("pistes-line")) map.removeLayer("pistes-line");
      if (map.getSource("pistes")) map.removeSource("pistes");
    }
  }, [pistes.length]);

  console.log(stations);

  return <div ref={containerRef} className="map-container" />;
});

export default MapView;
