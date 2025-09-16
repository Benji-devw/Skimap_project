import type { Piste } from "../types";
import "../styles/StyledPisteList.css";

type Props = {
  pistes: Piste[];
};

export default function PisteList({ pistes }: Props) {
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
            <span className="piste-name">{p.nom}</span>
            <div className="piste-row">
              <div className="piste-tags">
                {p.type && (
                  <span className={`tag tag-type tag-${p.type.toLowerCase()}`}>
                    {p.type}
                  </span>
                )}
                {p.etat && (
                  <span className={`tag tag-etat tag-${p.etat.toLowerCase()}`}>
                    {p.etat}
                  </span>
                )}
                {lengthLabel && (
                  <span className="tag tag-length">{lengthLabel}</span>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
