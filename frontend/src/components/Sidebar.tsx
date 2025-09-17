import type { Station, Piste } from "../types";
import PisteList from "./PisteList";

type Props = {
  pistes: Piste[];
  selectedStation: Station | null;
  setTargetPisteId: (id: number | null) => void;
};

export default function Sidebar({
  pistes,
  selectedStation,
  setTargetPisteId,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">
        🏘️ {selectedStation ? `– ${selectedStation.nom}` : ""}
      </div>
      <PisteList pistes={pistes} setTargetPisteId={setTargetPisteId} />
    </aside>
  );
}
