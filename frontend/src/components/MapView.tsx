import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import 'mapbox-gl/dist/mapbox-gl.css';
import type { Station, Piste, LineStringGeometry } from "../types";

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
  stations, setStations,
  pistes, setPistes,
  selectedStation, setSelectedStation,
  is3D
}: Props) {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [6.869, 45.923],
      zoom: 13
    });
    mapRef.current = map;

    map.on("load", () => {
      if (is3D) enable3D(map);
    });

    return () => map.remove();
  }, []);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/api/stations`)
      .then((r) => r.json())
      .then(setStations)
      .catch(console.error);
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    stations.forEach((station) => {
      const coord: [number, number] =
        station.geometry?.coordinates ?? [station.longitude, station.latitude];

      const marker = new mapboxgl.Marker()
        .setLngLat(coord)
        .setPopup(new mapboxgl.Popup().setText(station.nom))
        .addTo(map);

      marker.getElement().addEventListener("click", async () => {
        setSelectedStation(station);
        const pistesResp: Piste[] = await fetch(
          `${import.meta.env.VITE_API_URL}/api/pistes/?station_id=${station.id}`
        ).then((r) => r.json());
        setPistes(Array.isArray(pistesResp) ? pistesResp : []);
        renderPistesLayer(map, Array.isArray(pistesResp) ? pistesResp : []);
      });
    });
  }, [stations]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const apply = () => {
      if (is3D) enable3D(map);
      else disable3D(map);
    };

    if (map.isStyleLoaded()) {
      apply();
    } else {
      const onLoad = () => {
        apply();
        map.off('load', onLoad);
      };
      map.on('load', onLoad);
    }
  }, [is3D]);

  return <div ref={containerRef} className="map-container" />;
}

function renderPistesLayer(map: mapboxgl.Map, pistes: Piste[]) {
  const features = pistes
    .filter((p) => p.geometry)
    .map((p) => ({
      type: "Feature" as const,
      geometry: p.geometry as LineStringGeometry,
      properties: { nom: p.nom },
    }));

  const data = { type: "FeatureCollection" as const, features };

  if (map.getSource("pistes")) {
    if (map.getLayer("pistes-line")) map.removeLayer("pistes-line");
    map.removeSource("pistes");
  }
  map.addSource("pistes", { type: "geojson", data });
  map.addLayer({
    id: "pistes-line",
    type: "line",
    source: "pistes",
    paint: { "line-color": "#ff3b3b", "line-width": 3 },
  });
}

function enable3D(map: mapboxgl.Map) {
  if (!map.getSource("mapbox-dem")) {
    map.addSource("mapbox-dem", {
      type: "raster-dem",
      url: "mapbox://mapbox.terrain-rgb",
      tileSize: 512,
      maxzoom: 14,
    } as any);
  }
  map.setTerrain({ source: "mapbox-dem", exaggeration: 1.5 });
  map.easeTo({ pitch: 60, bearing: 20, duration: 1000 });
}

function disable3D(map: mapboxgl.Map) {
  map.setTerrain(null);
  map.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
}
