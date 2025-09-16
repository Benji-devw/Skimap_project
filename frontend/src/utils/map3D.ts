import mapboxgl from "mapbox-gl";

export function enable3D(map: mapboxgl.Map) {
  if (!map.getSource("mapbox-dem")) {
    map.addSource("mapbox-dem", {
      type: "raster-dem",
      url: "mapbox://mapbox.terrain-rgb",
      tileSize: 512,
      maxzoom: 14,
    } as any);
  }

  // Animation de l'effet "montagne qui pousse"
  let startTime: number | null = null;
  const duration = 1000; // 1 secondes
  const startExaggeration = 0;
  const targetExaggeration = 1.5;

  function animate(time: number) {
    if (!startTime) startTime = time;
    const elapsed = time - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // Calcul de l'exagération courante
    const currentExaggeration =
      startExaggeration + progress * (targetExaggeration - startExaggeration);

    map.setTerrain({ source: "mapbox-dem", exaggeration: currentExaggeration });

    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }

  requestAnimationFrame(animate);
  map.easeTo({ duration: 2000 });
}

export function disable3D(map: mapboxgl.Map) {
  map.setTerrain(null);
  map.easeTo({ duration: 2000 });
}
