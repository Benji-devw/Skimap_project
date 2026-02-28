import { useCallback, useRef, useState } from "react";
import "./App.css";
import type { Station, Piste, SnowMeasure } from "./types";
import MapView, { type MapViewHandle } from "./components/MapView";
import Topbar from "./components/Topbar";
import Sidebar from "./components/Sidebar";
import CustomMapbar from "./components/CustomMapbar";
import PisteDrawer from "./components/PisteDrawer";

export default function App() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [pistes, setPistes] = useState<Piste[]>([]);
  const [snowMeasures, setSnowMeasures] = useState<SnowMeasure[]>([]);
  const [targetPisteId, setTargetPisteId] = useState<number | null>(null);
  const [is3D, setIs3D] = useState(false);
  const [isSatellite, setIsSatellite] = useState(false);
  const [isDrawing, setIsDrawing] = useState(false);
  const [showSnowLayer, setShowSnowLayer] = useState(false);
  const [hasSnowLayer, setHasSnowLayer] = useState(false);

  // Fetch le statut neige pour une station et met à jour hasSnowLayer
  const refreshSnowLayerStatus = useCallback(async (stationId: number) => {
    try {
      const r = await fetch(
        `${import.meta.env.VITE_API_URL}/api/lidar/status/?station_id=${stationId}`,
      );
      const data = await r.json();
      setHasSnowLayer(data.snow_layer_ready === true);
    } catch {
      setHasSnowLayer(false);
    }
  }, []);

  const handleSetSelectedStation = (station: Station | null) => {
    if (!station) {
      setShowSnowLayer(false);
      setHasSnowLayer(false);
      setSelectedStation(null);
      return;
    }
    // Si on change de station, reset d'abord puis re-fetch
    if (station.id !== selectedStation?.id) {
      setShowSnowLayer(false);
      setHasSnowLayer(false);
    }
    setSelectedStation(station);
    // Re-fetch dans tous les cas (même station, même id) pour
    // remettre hasSnowLayer à jour si on a recliqué sur le même marker
    refreshSnowLayerStatus(station.id);
  };
  const [drawCoordinates, setDrawCoordinates] = useState<[number, number][]>(
    [],
  );
  const mapViewRef = useRef<MapViewHandle | null>(null);

  const handlePisteCreated = async () => {
    // Recharger les pistes de la station sélectionnée
    if (selectedStation) {
      const pistesResp: Piste[] = await fetch(
        `${import.meta.env.VITE_API_URL}/api/pistes/?station_id=${selectedStation.id}`,
      ).then((r) => r.json());
      setPistes(Array.isArray(pistesResp) ? pistesResp : []);
    }
  };

  return (
    <>
      <MapView
        ref={mapViewRef}
        stations={stations}
        setStations={setStations}
        pistes={pistes}
        setPistes={setPistes}
        snowMeasures={snowMeasures}
        setSnowMeasures={setSnowMeasures}
        selectedStation={selectedStation}
        setSelectedStation={handleSetSelectedStation}
        selectedStationId={selectedStation?.id ?? null}
        is3D={is3D}
        isSatellite={isSatellite}
        targetPisteId={targetPisteId}
        setTargetPisteId={setTargetPisteId}
        isDrawing={isDrawing}
        showSnowLayer={showSnowLayer}
        coordinates={drawCoordinates}
        setCoordinates={setDrawCoordinates}
      />
      <div className="ui">
        <Topbar
          selectedStation={selectedStation}
          clearPistes={() => {
            setPistes([]);
            handleSetSelectedStation(null);
            setTargetPisteId(null);
          }}
        />
        <CustomMapbar
          is3D={is3D}
          setIs3D={setIs3D}
          isSatellite={isSatellite}
          setIsSatellite={setIsSatellite}
          showSnowLayer={showSnowLayer}
          setShowSnowLayer={(v) => {
            // Désactiver la couche si on change de station sans LAZ
            if (!hasSnowLayer) return;
            setShowSnowLayer(v);
          }}
          hasSnowLayer={hasSnowLayer}
          selectedStation={selectedStation}
          onResetBearing={() => mapViewRef.current?.resetBearing()}
        />
        <Sidebar
          pistes={pistes}
          selectedStation={selectedStation}
          setTargetPisteId={setTargetPisteId}
          onPisteDeleted={handlePisteCreated}
          onSnowLayerReady={() => {
            setHasSnowLayer(true);
          }}
          onSnowLayerRemoved={() => {
            setShowSnowLayer(false);
            setHasSnowLayer(false);
          }}
        />
        <PisteDrawer
          selectedStation={selectedStation}
          isDrawing={isDrawing}
          setIsDrawing={setIsDrawing}
          onPisteCreated={handlePisteCreated}
          coordinates={drawCoordinates}
          setCoordinates={setDrawCoordinates}
        />
      </div>
    </>
  );
}
