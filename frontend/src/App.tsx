import { useState } from "react";
import './App.css';
import type { Station, Piste } from "./types";
import MapView from "./components/MapView";
import Topbar from "./components/Topbar";
import Sidebar from "./components/Sidebar";
import CustomMapbar from "./components/CustomMapbar";

export default function App() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selectedStation, setSelectedStation] = useState<Station | null>(null);
  const [pistes, setPistes] = useState<Piste[]>([]);
  const [is3D, setIs3D] = useState(false);
  const [isSatellite, setIsSatellite] = useState(false);

  return (
    <>
      <MapView
        stations={stations}
        setStations={setStations}
        pistes={pistes}
        setPistes={setPistes}
        selectedStation={selectedStation}
        setSelectedStation={setSelectedStation}
        is3D={is3D}
        // isSatellite={isSatellite}
      />
      <div className="ui">
        <Topbar
          selectedStation={selectedStation}
          clearPistes={() => setPistes([])}
        />
        <CustomMapbar
          is3D={is3D}
          setIs3D={setIs3D}
          isSatellite={isSatellite}
          setIsSatellite={setIsSatellite}
        />
        <Sidebar
          pistes={pistes}
          selectedStation={selectedStation}
        />
      </div>
    </>
  );
}
