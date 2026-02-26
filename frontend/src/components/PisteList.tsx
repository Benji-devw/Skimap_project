import type { Piste } from "../types";
import "../styles/StyledPisteList.css";

type Props = {
  pistes: Piste[];
  setTargetPisteId: (id: number | null) => void;
  onPisteDeleted: () => void;
};

export default function PisteList({
  pistes,
  setTargetPisteId,
  onPisteDeleted,
}: Props) {
  const handleDelete = async (
    e: React.MouseEvent,
    pisteId: number,
    pisteName: string,
  ) => {
    e.stopPropagation(); // Empêcher le zoom sur la piste lors du clic sur supprimer

    const confirmation = confirm(
      `🗑️ Voulez-vous vraiment supprimer la piste "${pisteName}" ?\n\nCette action est irréversible.`,
    );

    if (!confirmation) return;

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/pistes/${pisteId}/`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        throw new Error("Erreur lors de la suppression");
      }

      alert(`✅ Piste "${pisteName}" supprimée avec succès !`);
      onPisteDeleted();
    } catch (err) {
      console.error("❌ Erreur lors de la suppression:", err);
      alert(
        `❌ Impossible de supprimer la piste.\n${err instanceof Error ? err.message : "Erreur inconnue"}`,
      );
    }
  };

  if (pistes.length === 0) {
    return (
      <div className="sidebar-empty">
        Cliquez un marker pour charger les pistes.
      </div>
    );
  }

  return (
    <ul className="piste-list">
      {pistes.map((p) => {
        const lengthLabel =
          typeof p.longueur === "number" && !Number.isNaN(p.longueur)
            ? p.longueur >= 1000
              ? `${(p.longueur / 1000).toFixed(1)} km`
              : `${p.longueur} m`
            : "";
        return (
          <li key={p.id} className="piste-item">
            <div
              className="piste-content"
              onClick={() => setTargetPisteId(p.id)}
            >
              <span className="piste-name">⛷️ {p.nom}</span>
              <div className="piste-row">
                <div className="piste-tags">
                  {p.type && (
                    <span
                      className={`tag tag-type tag-${p.type.toLowerCase()}`}
                    >
                      Type : {p.type}
                    </span>
                  )}
                  {p.etat && (
                    <span
                      className={`tag tag-etat tag-${p.etat.toLowerCase()}`}
                    >
                      Statut : {p.etat}
                    </span>
                  )}
                  {lengthLabel && (
                    <span className="tag tag-length">
                      Distance : {lengthLabel}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              className="delete-btn"
              onClick={(e) => handleDelete(e, p.id, p.nom)}
              title="Supprimer cette piste"
              aria-label={`Supprimer ${p.nom}`}
            >
              🗑️
            </button>
          </li>
        );
      })}
    </ul>
  );
}
