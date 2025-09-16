import type { Station, Piste } from "../types";
import PisteList from "./PisteList";

type Props = {
  pistes: Piste[];
  selectedStation: Station | null;
};

export default function Sidebar({ pistes, selectedStation }: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">
        Pistes {selectedStation ? `– ${selectedStation.nom}` : ""}
      </div>
      <PisteList pistes={pistes} />
    </aside>
  );
}
