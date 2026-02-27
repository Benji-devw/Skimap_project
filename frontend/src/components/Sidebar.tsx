import type { Station, Piste } from "../types";
import PisteList from "./PisteList";
import StationWeather from "./StationWeather";
import LidarUploader from "./LidarUploader";

type Props = {
  pistes: Piste[];
  selectedStation: Station | null;
  setTargetPisteId: (id: number | null) => void;
  onPisteDeleted: () => void;
  onSnowLayerReady: () => void;
  onSnowLayerRemoved: () => void;
};

export default function Sidebar({
  pistes,
  selectedStation,
  setTargetPisteId,
  onPisteDeleted,
  onSnowLayerReady,
  onSnowLayerRemoved,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">
        🏘️ {selectedStation ? `– ${selectedStation.nom}` : ""}
      </div>
      {selectedStation && <StationWeather station={selectedStation} />}
      {selectedStation && (
        <LidarUploader
          station={selectedStation}
          onSnowLayerReady={onSnowLayerReady}
          onSnowLayerRemoved={onSnowLayerRemoved}
        />
      )}
      <PisteList
        pistes={pistes}
        setTargetPisteId={setTargetPisteId}
        onPisteDeleted={onPisteDeleted}
      />
    </aside>
  );
}
