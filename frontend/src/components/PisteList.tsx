import type { Piste } from "../types";

type Props = {
  pistes: Piste[];
};

export default function PisteList({ pistes }: Props) {
  if (pistes.length === 0) {
    return <div className="sidebar-empty">Cliquez un marker pour charger les pistes.</div>;
  }

  return (
    <ul className="piste-list">
      {pistes.map((p) => (
        <li key={p.id} className={`piste-item`}>
          
          <ul className="piste-details"> <span className="piste-name">{p.nom}</span>
            <li className="piste-type">{p.type}</li>
            <li className="piste-etat">{p.etat}</li>
            <li className="piste-longueur">{p.longueur}</li>
            {/* add longitude and latitude */}
            <li className="piste-longitude">{p.geometry?.coordinates[0]}</li>
            <li className="piste-latitude">{p.geometry?.coordinates[1]}</li>
          </ul>
        </li>
      ))}
    </ul>
  );
}
