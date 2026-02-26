import { useState } from "react";
import type { Station } from "../types";

type Props = {
  selectedStation: Station | null;
  isDrawing: boolean;
  setIsDrawing: (drawing: boolean) => void;
  onPisteCreated: () => void;
  coordinates: [number, number][];
  setCoordinates: (coords: [number, number][]) => void;
};

export default function PisteDrawer({
  selectedStation,
  isDrawing,
  setIsDrawing,
  onPisteCreated,
  coordinates,
  setCoordinates,
}: Props) {
  const [nom, setNom] = useState("");
  const [type, setType] = useState("verte");
  const [etat, setEtat] = useState("ouverte");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartDrawing = () => {
    if (!selectedStation) {
      alert("Veuillez d'abord sélectionner une station");
      return;
    }
    setCoordinates([]);
    setIsDrawing(true);
    setError(null);
  };

  const handleCancelDrawing = () => {
    setIsDrawing(false);
    setCoordinates([]);
    setNom("");
    setError(null);
  };

  const handleSave = async () => {
    if (!selectedStation) {
      setError("Aucune station sélectionnée");
      return;
    }

    if (coordinates.length < 2) {
      setError("Veuillez tracer au moins 2 points");
      return;
    }

    if (!nom.trim()) {
      setError("Veuillez entrer un nom pour la piste");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Calculer la longueur approximative (en mètres)
      const longueur = calculateLength(coordinates);

      const payload = {
        station_id: selectedStation.id,
        nom: nom.trim(),
        type,
        etat,
        longueur: Math.round(longueur),
        geometry: {
          type: "LineString",
          coordinates,
        },
      };

      console.log("📤 Envoi de la piste:", payload);

      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/pistes/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        },
      );

      console.log("📥 Réponse status:", response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("❌ Erreur backend:", errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          throw new Error(`Erreur ${response.status}: ${errorText}`);
        }

        // Afficher les erreurs de validation
        if (errorData.geometry) {
          throw new Error(`Géométrie: ${JSON.stringify(errorData.geometry)}`);
        }
        if (errorData.station_id) {
          throw new Error(`Station: ${JSON.stringify(errorData.station_id)}`);
        }

        throw new Error(
          errorData.detail ||
            JSON.stringify(errorData) ||
            "Erreur lors de la création",
        );
      }

      const result = await response.json();
      console.log("✅ Piste créée:", result);

      // Réinitialiser le formulaire
      setNom("");
      setType("verte");
      setEtat("ouverte");
      setCoordinates([]);
      setIsDrawing(false);
      onPisteCreated();

      // Message de succès avec plus d'informations
      alert(
        `✅ Piste créée avec succès !\n\n📛 ${nom}\n📏 ${Math.round(longueur)}m\n🎿 ${type}\n${etat === "ouverte" ? "✅" : "❌"} ${etat}`,
      );
    } catch (err) {
      console.error("❌ Erreur complète:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Erreur inconnue";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Calculer la longueur approximative en mètres (formule de Haversine simplifiée)
  const calculateLength = (coords: [number, number][]): number => {
    let length = 0;
    for (let i = 0; i < coords.length - 1; i++) {
      const [lon1, lat1] = coords[i];
      const [lon2, lat2] = coords[i + 1];
      length += getDistance(lat1, lon1, lat2, lon2);
    }
    return length;
  };

  const getDistance = (
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number,
  ): number => {
    const R = 6371e3; // Rayon de la Terre en mètres
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    const Δφ = ((lat2 - lat1) * Math.PI) / 180;
    const Δλ = ((lon2 - lon1) * Math.PI) / 180;

    const a =
      Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
      Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
  };

  if (!selectedStation) {
    return null;
  }

  return (
    <div className="piste-drawer">
      <h3>✏️ Tracer une nouvelle piste</h3>

      {!isDrawing ? (
        <button
          onClick={handleStartDrawing}
          title="Commencer à tracer une nouvelle piste"
        >
          🖊️ Commencer le tracé
        </button>
      ) : (
        <div className="drawing-controls">
          <p className="info">
            🖱️ Cliquez sur la carte pour ajouter des points
            <br />
            📍 Points tracés: {coordinates.length}
          </p>

          <input
            type="text"
            placeholder="Nom de la piste"
            value={nom}
            onChange={(e) => setNom(e.target.value)}
          />

          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="verte">🟢 Verte</option>
            <option value="bleue">🔵 Bleue</option>
            <option value="rouge">🔴 Rouge</option>
            <option value="noire">⚫ Noire</option>
          </select>

          <select value={etat} onChange={(e) => setEtat(e.target.value)}>
            <option value="ouverte">✅ Ouverte</option>
            <option value="fermee">❌ Fermée</option>
          </select>

          {error && <div className="error">{error}</div>}

          <div className="button-group">
            <button
              onClick={handleSave}
              disabled={loading || coordinates.length < 2}
            >
              {loading ? "Enregistrement..." : "💾 Sauvegarder"}
            </button>
            <button onClick={handleCancelDrawing} disabled={loading}>
              ❌ Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
