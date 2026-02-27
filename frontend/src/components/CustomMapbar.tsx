import "../styles/StyledCustomMapButton.css";
import type { Station } from "../types";

type Props = {
  is3D: boolean;
  setIs3D: (v: boolean) => void;
  isSatellite: boolean;
  setIsSatellite: (v: boolean) => void;
  showSnowLayer: boolean;
  setShowSnowLayer: (v: boolean) => void;
  hasSnowLayer: boolean;
  selectedStation: Station | null;
  onResetBearing: () => void;
};

export default function CustomMapbar({
  is3D,
  setIs3D,
  isSatellite,
  setIsSatellite,
  showSnowLayer,
  setShowSnowLayer,
  hasSnowLayer,
  selectedStation,
  onResetBearing,
}: Props) {
  const isSnowButtonDisabled = !selectedStation || !hasSnowLayer;

  const snowButtonTooltip = !selectedStation
    ? "Sélectionnez une station pour voir la couche de neige"
    : !hasSnowLayer
      ? `Données LIDAR non disponibles pour ${selectedStation.nom} (disponible uniquement pour Ancelle)`
      : showSnowLayer
        ? "Désactiver la couche de neige"
        : "Activer la couche de neige LIDAR";
  return (
    <div className="custom-mapbar">
      <button className="styled-button" onClick={() => setIs3D(!is3D)}>
        {is3D ? "Vue 2D" : "Vue 3D"}
      </button>

      <button
        className="styled-button"
        onClick={() => setIsSatellite(!isSatellite)}
      >
        {isSatellite ? "Satellite: ON" : "Satellite: OFF"}
        <span className="inner-button">
          <span className="icon">🛰️</span>
        </span>
      </button>

      {/* Bouton pour afficher/cacher la couche de neige */}
      <div style={{ position: "relative" }}>
        <button
          className="styled-button"
          onClick={() =>
            !isSnowButtonDisabled && setShowSnowLayer(!showSnowLayer)
          }
          disabled={isSnowButtonDisabled}
          style={{
            backgroundColor: showSnowLayer ? "#00CCFF" : undefined,
            opacity: isSnowButtonDisabled ? 0.5 : 1,
            cursor: isSnowButtonDisabled ? "not-allowed" : "pointer",
          }}
          title={snowButtonTooltip}
        >
          {showSnowLayer ? "Neige: ON" : "Neige: OFF"}
          <span className="inner-button">
            <span className="icon">❄️</span>
          </span>
        </button>
      </div>

      {/* Nouveau bouton pour réinitialiser le bearing */}
      <button className="styled-button" onClick={onResetBearing}>
        Nord ↑
      </button>
    </div>
  );
}
