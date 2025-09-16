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
        <li key={p.id} className="piste-item">
          <span className="piste-name">{p.nom}</span>
        </li>
      ))}
    </ul>
  );
}
