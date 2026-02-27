import { useRef, useState } from "react";

// ID de la station qui possède un fichier LAZ → carte de neige disponible
const LIDAR_STATION_ID = 3; // Ancelle
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
  const hasSnowLayer = selectedStation?.id === LIDAR_STATION_ID;

  const handleSetSelectedStation = (station: Station | null) => {
    // Si on change de station et que la nouvelle n'a pas de LAZ, on cache la couche neige
    if (station?.id !== LIDAR_STATION_ID) {
      setShowSnowLayer(false);
    }
    setSelectedStation(station);
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
