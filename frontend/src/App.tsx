import { useRef, useState } from "react";
import "./App.css";
import type { Station, Piste, SnowMeasure } from "./types";
import MapView, { type MapViewHandle } from "./components/MapView";
import Topbar from "./components/Topbar";
import Sidebar from "./components/Sidebar";
import CustomMapbar from "./components/CustomMapbar";

export default function App() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [pistes, setPistes] = useState<Piste[]>([]);
  const [snowMeasures, setSnowMeasures] = useState<SnowMeasure[]>([]);
  const [targetPisteId, setTargetPisteId] = useState<number | null>(null);
  const [is3D, setIs3D] = useState(false);
  const [isSatellite, setIsSatellite] = useState(false);
  const mapViewRef = useRef<MapViewHandle | null>(null);

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
        setSelectedStation={setSelectedStation}
        is3D={is3D}
        isSatellite={isSatellite}
        targetPisteId={targetPisteId}
        setTargetPisteId={setTargetPisteId}
      />
      <div className="ui">
        <Topbar
          selectedStation={selectedStation}
          clearPistes={() => {
            setPistes([]);
            setSelectedStation(null);
            setTargetPisteId(null);
          }}
        />
        <CustomMapbar
          is3D={is3D}
          setIs3D={setIs3D}
          isSatellite={isSatellite}
          setIsSatellite={setIsSatellite}
          onResetBearing={() => mapViewRef.current?.resetBearing()}
        />
        <Sidebar
          pistes={pistes}
          selectedStation={selectedStation}
          setTargetPisteId={setTargetPisteId}
        />
      </div>
    </>
  );
}
