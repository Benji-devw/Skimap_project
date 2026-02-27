import type { Station, Piste } from "../types";
import PisteList from "./PisteList";
import StationWeather from "./StationWeather";

type Props = {
  pistes: Piste[];
  selectedStation: Station | null;
  setTargetPisteId: (id: number | null) => void;
  onPisteDeleted: () => void;
};

export default function Sidebar({
  pistes,
  selectedStation,
  setTargetPisteId,
  onPisteDeleted,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">
        🏘️ {selectedStation ? `– ${selectedStation.nom}` : ""}
      </div>
      {selectedStation && <StationWeather station={selectedStation} />}
      <PisteList
        pistes={pistes}
        setTargetPisteId={setTargetPisteId}
        onPisteDeleted={onPisteDeleted}
      />
    </aside>
  );
}
