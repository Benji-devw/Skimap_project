import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import type { Station, Piste, SnowMeasure } from "../types";
import { enable3D, disable3D } from "../utils/map3D";
import { renderPistesLayer } from "../utils/pistesLayer";

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN as string;

type Props = {
  stations: Station[];
  setStations: (s: Station[]) => void;
  pistes: Piste[];
  setPistes: (p: Piste[]) => void;
  snowMeasures: SnowMeasure[];
  setSnowMeasures: (s: SnowMeasure[]) => void;
  selectedStation: Station | null;
  setSelectedStation: (s: Station | null) => void;
  is3D: boolean;
  isSatellite: boolean;
  targetPisteId: number | null;
  setTargetPisteId: (id: number | null) => void;
  isDrawing: boolean;
  coordinates: [number, number][];
  setCoordinates: (coords: [number, number][]) => void;
};

export type MapViewHandle = {
  resetBearing: () => void;
};

const MapView = forwardRef<MapViewHandle, Props>(
  (
    {
      stations,
      setStations,
      pistes,
      setPistes,
      snowMeasures,
      setSnowMeasures,
      setSelectedStation,
      is3D,
      isSatellite,
      targetPisteId,
      setTargetPisteId,
      isDrawing,
      coordinates,
      setCoordinates,
    },
    ref,
  ) => {
    const mapRef = useRef<mapboxgl.Map | null>(null);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const markersRef = useRef<mapboxgl.Marker[]>([]);

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
        center: [6.201809, 44.620601],
        zoom: 13,
        bearing: 0,
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

    // Fetch snow measures
    useEffect(() => {
      fetch(`${import.meta.env.VITE_API_URL}/api/snow_measures`)
        .then((r) => r.json())
        .then(setSnowMeasures)
        .catch(console.error);
    }, []);

    // Toggle 3D
    useEffect(() => {
      const map = mapRef.current;
      if (!map) return;

      if (map.isStyleLoaded()) {
        if (is3D) {
          enable3D(map);
        } else {
          disable3D(map);
        }
      } else {
        map.once("load", () => {
          if (is3D) {
            enable3D(map);
          } else {
            disable3D(map);
          }
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

    // Add markers for stations
    useEffect(() => {
      const map = mapRef.current;
      if (!map) return;

      stations.forEach((station) => {
        const coord = station.geometry?.coordinates ?? [
          station.longitude,
          station.latitude,
        ];

        // Find last snow measure for this station
        const lastSnowMeasure = snowMeasures
          .filter((s) => s.station.id === station.id)
          .reduce((latest: SnowMeasure | null, current: SnowMeasure) => {
            return !latest ||
              new Date(current.date_time) > new Date(latest.date_time)
              ? current
              : latest;
          }, null);

        const popupContent = lastSnowMeasure
          ? `
        <b>${station.nom}</b><br/><hr/>
        📅 ${new Date(lastSnowMeasure.date_time).toLocaleDateString()}<br/>
        🌡 ${lastSnowMeasure.temperature_c}°C<br/>
        🌧 ${lastSnowMeasure.precipitation_mm} mm<br/>
        ❄️ Total: ${lastSnowMeasure.total_snow_height_cm} cm<br/>
        ⛰ Naturelle: ${lastSnowMeasure.natural_snow_height_cm} cm<br/>
        🏔 Artificielle: ${lastSnowMeasure.artificial_snow_height_cm} cm<br/>
        💧 Production: ${lastSnowMeasure.artificial_snow_production_m3} m³
      `
          : `<b>${station.nom}</b><hr/>`;

        const marker = new mapboxgl.Marker()
          .setLngLat(coord)
          .setPopup(new mapboxgl.Popup().setHTML(popupContent))
          .addTo(map);

        marker.getElement().addEventListener("click", async () => {
          setSelectedStation(station);
          // Zoom to station selected
          const target = station.geometry?.coordinates ?? [
            station.longitude,
            station.latitude,
          ];
          map.easeTo({
            center: target as [number, number],
            pitch: 50,
            zoom: 13,
            duration: 800,
          });
          // clear target piste to avoid re-zooming on previous selection
          setTargetPisteId(null);

          const pistesResp: Piste[] = await fetch(
            `${import.meta.env.VITE_API_URL}/api/pistes/?station_id=${
              station.id
            }`,
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
      if (typeof targetPisteId !== "number") return;
      const piste = pistes.find((p) => p.id === targetPisteId);
      if (!piste || !piste.geometry) return;
      const coords = piste.geometry.coordinates;
      if (!coords || coords.length === 0) return;
      map.easeTo({
        center: coords[0] as [number, number],
        pitch: 50,
        zoom: 14,
        duration: 700,
      });
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

    // Handle drawing mode - add click event listener
    useEffect(() => {
      const map = mapRef.current;
      if (!map) return;

      const handleMapClick = (e: mapboxgl.MapMouseEvent) => {
        if (!isDrawing) return;

        const { lng, lat } = e.lngLat;
        const newCoords: [number, number][] = [...coordinates, [lng, lat]];
        setCoordinates(newCoords);

        // Add a marker for the clicked point
        const marker = new mapboxgl.Marker({ color: "#FF0000", scale: 0.8 })
          .setLngLat([lng, lat])
          .addTo(map);
        markersRef.current.push(marker);

        // Update or create the drawing line
        updateDrawingLine(map, newCoords);
      };

      if (isDrawing) {
        map.getCanvas().style.cursor = "crosshair";
        map.on("click", handleMapClick);
      } else {
        map.getCanvas().style.cursor = "";
        // Clean up markers when not drawing
        markersRef.current.forEach((m) => m.remove());
        markersRef.current = [];
        // Remove drawing layer
        if (map.getLayer("drawing-line")) map.removeLayer("drawing-line");
        if (map.getSource("drawing")) map.removeSource("drawing");
      }

      return () => {
        map.off("click", handleMapClick);
      };
    }, [isDrawing, coordinates]);

    // Update drawing line on the map
    const updateDrawingLine = (
      map: mapboxgl.Map,
      coords: [number, number][],
    ) => {
      const geojson: GeoJSON.Feature<GeoJSON.LineString> = {
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: coords,
        },
      };

      if (map.getSource("drawing")) {
        (map.getSource("drawing") as mapboxgl.GeoJSONSource).setData(geojson);
      } else {
        map.addSource("drawing", {
          type: "geojson",
          data: geojson,
        });

        map.addLayer({
          id: "drawing-line",
          type: "line",
          source: "drawing",
          paint: {
            "line-color": "#FF0000",
            "line-width": 4,
            "line-opacity": 0.8,
          },
        });
      }
    };

    // console.log(stations);
    // console.log(targetPisteId);
    // console.log(snowMeasures);

    return <div ref={containerRef} className="map-container" />;
  },
);

export default MapView;
