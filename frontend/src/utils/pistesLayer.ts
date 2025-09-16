import type { Piste, LineStringGeometry } from "../types";

export function renderPistesLayer(map: mapboxgl.Map, pistes: Piste[]) {
  const features = pistes
    .filter((p) => p.geometry)
    .map((p) => ({
      type: "Feature" as const,
      geometry: p.geometry as LineStringGeometry,
      properties: { nom: p.nom + " " + p.type + " " + p.etat + " " + p.longueur },
    }));

  const data = { type: "FeatureCollection" as const, features };

  if (map.getSource("pistes")) {
    if (map.getLayer("pistes-line")) map.removeLayer("pistes-line");
    map.removeSource("pistes");
  }

  map.addSource("pistes", { type: "geojson", data });
  map.addLayer({
    id: "pistes-line",
    type: "line",
    source: "pistes",
    paint: { "line-color": "#ff3b3b", "line-width": 3 },
  });
}
