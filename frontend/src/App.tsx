import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import './App.css';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN as string;

type LineStringGeometry = {
  type: 'LineString';
  coordinates: [number, number][];
};

type Piste = {
  id: number;
  nom: string;
  geometry: LineStringGeometry | null;
};

type Station = {
  id: number;
  nom: string;
  longitude: number;
  latitude: number;
};


export default function App() {
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [pistes, setPistes] = useState<Piste[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [6.869, 45.923] as [number, number],
      zoom: 13
    });
    mapRef.current = map;
    return () => map.remove();
  }, []);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/stations/stations`)
      .then((r) => r.json() as Promise<Station[]>)
      .then(setStations)
      .catch((err) => console.error(err));
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    stations.forEach((s: Station) => {
      const marker = new mapboxgl.Marker()
        .setLngLat([s.longitude, s.latitude] as [number, number])
        .setPopup(new mapboxgl.Popup().setText(s.nom))
        .addTo(map);

      marker.getElement().addEventListener('click', async () => {
        setSelectedStation(s);
        const pistesResp: Piste[] = await fetch(`${import.meta.env.VITE_API_URL}/stations/pistes/${s.id}`)
          .then((r) => r.json());
        setPistes(pistesResp);
        renderPistesLayer(map, pistesResp);
      });
    });
  }, [stations]);

  function renderPistesLayer(map: mapboxgl.Map, pistesList: Piste[]) {
    const features = (pistesList || [])
      .filter((p) => p.geometry)
      .map((p) => ({
        type: 'Feature' as const,
        geometry: p.geometry as LineStringGeometry,
        properties: { nom: p.nom }
      }));
    const data = { type: 'FeatureCollection' as const, features };

    if (map.getSource('pistes')) {
      if (map.getLayer('pistes-line')) map.removeLayer('pistes-line');
      map.removeSource('pistes');
    }
    map.addSource('pistes', { type: 'geojson', data });
    map.addLayer({
      id: 'pistes-line',
      type: 'line',
      source: 'pistes',
      paint: { 'line-color': '#ff3b3b', 'line-width': 3 }
    });

    const coords: [number, number][] = features.flatMap((f) => f.geometry.coordinates);
    if (coords.length > 0) {
      const bounds = coords.reduce(
        (b, [lng, lat]) => b.extend([lng, lat] as [number, number]),
        new mapboxgl.LngLatBounds(coords[0], coords[0])
      );
      map.fitBounds(bounds, { padding: 40, maxZoom: 14 });
    }
  }

  function clearPistes() {
    const map = mapRef.current;
    if (!map) return;
    if (map.getSource('pistes')) {
      if (map.getLayer('pistes-line')) map.removeLayer('pistes-line');
      map.removeSource('pistes');
    }
    setPistes([]);
    setSelectedStation(null);
  }

  function zoomToPiste(geometry: LineStringGeometry) {
    const map = mapRef.current;
    if (!map) return;
    const coords: [number, number][] = geometry.coordinates;
    if (coords.length > 0) {
      const bounds = coords.reduce(
        (b, [lng, lat]) => b.extend([lng, lat] as [number, number]),
        new mapboxgl.LngLatBounds(coords[0], coords[0])
      );
      map.fitBounds(bounds, { padding: 40, maxZoom: 15 });
    }
  }

  return (
    <>
      <div ref={containerRef} className="map-container" />
      <div className="ui">
        <div className="topbar">
          <div className="brand">SkiMap</div>
          <div className="spacer" />
          <div className="status">{selectedStation ? selectedStation.nom : 'Sélectionnez une station'}</div>
          <button className="btn" onClick={clearPistes}>Effacer</button>
        </div>
        <aside className="sidebar">
          <div className="sidebar-title">Pistes {selectedStation ? `– ${selectedStation.nom}` : ''}</div>
          {pistes.length === 0 ? (
            <div className="sidebar-empty">Cliquez un marker pour charger les pistes.</div>
          ) : (
            <ul className="piste-list">
              {pistes.map((p) => (
                <li key={p.id} className="piste-item">
                  <span className="piste-name">{p.nom}</span>
                  {p.geometry && (
                    <button className="btn btn-small" onClick={() => zoomToPiste(p.geometry!)}>Zoom</button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </>
  );
}