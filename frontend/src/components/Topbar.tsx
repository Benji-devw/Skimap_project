import type { Station } from "../types";

type Props = {
  selectedStation: Station | null;
  clearPistes: () => void;
};

export default function Topbar({ selectedStation, clearPistes }: Props) {
  return (
    <div className="topbar">
      <div className="brand">SkiMap</div>
      <div className="spacer" />
      <div className="status">{selectedStation ? selectedStation.nom : "Sélectionnez une station"}</div>
      <button className="btn" onClick={clearPistes}>Effacer</button>
    </div>
  );
}
