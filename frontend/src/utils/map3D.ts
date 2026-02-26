function animateTerrain(
  map: mapboxgl.Map,
  startExaggeration: number,
  targetExaggeration: number,
  startPitch: number,
  targetPitch: number,
  duration = 1000,
) {
  // Check if the source 'mapbox-dem' exists
  if (!map.getSource("mapbox-dem")) {
    console.warn("Source 'mapbox-dem' not found. Skipping terrain animation.");
    return;
  }

  let startTime: number | null = null;

  function animate(time: number) {
    if (!startTime) startTime = time;
    const elapsed = time - startTime;
    const progress = Math.min(elapsed / duration, 1);

    const currentExaggeration =
      startExaggeration + progress * (targetExaggeration - startExaggeration);

    const currentPitch = startPitch + progress * (targetPitch - startPitch);

    if (targetExaggeration > 0) {
      map.setTerrain({
        source: "mapbox-dem",
        exaggeration: currentExaggeration,
      });
    } else {
      map.setTerrain(
        progress < 1
          ? { source: "mapbox-dem", exaggeration: currentExaggeration }
          : null,
      );
    }

    map.setPitch(currentPitch);

    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }

  requestAnimationFrame(animate);
}

export function enable3D(map: mapboxgl.Map, instant = false) {
  const sourceExists = map.getSource("mapbox-dem");

  if (!sourceExists) {
    map.addSource("mapbox-dem", {
      type: "raster-dem",
      url: "mapbox://mapbox.terrain-rgb",
      tileSize: 512,
      maxzoom: 14,
    } as any);
  }

  if (instant) {
    // Mode instantané : pas d'animation (pour les changements de style)
    // Activer le terrain immédiatement, Mapbox chargera les tuiles en arrière-plan
    map.setTerrain({ source: "mapbox-dem", exaggeration: 1.5 });

    // Maintenir le pitch actuel (déjà restauré par jumpTo dans MapView)
    // Ne pas forcer un pitch spécifique pour éviter les sauts visuels
  } else {
    // Mode animé : transition fluide (pour l'activation manuelle)
    const startPitch = map.getPitch();
    animateTerrain(map, 0, 1.5, startPitch, 70, 1000);
  }
}

export function disable3D(map: mapboxgl.Map, instant = false) {
  const terrain = map.getTerrain();
  const startExaggeration = terrain ? (terrain.exaggeration as number) : 0;
  const startPitch = map.getPitch();

  if (instant) {
    // Mode instantané : désactivation immédiate
    map.setTerrain(null);
    map.setPitch(0);
  } else {
    // Mode animé : transition fluide
    animateTerrain(map, startExaggeration, 0, startPitch, 0, 1000);
  }
}
