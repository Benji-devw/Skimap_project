function animateTerrain(
  map: mapboxgl.Map,
  startExaggeration: number,
  targetExaggeration: number,
  startPitch: number,
  targetPitch: number,
  duration = 1000
) {
  let startTime: number | null = null;

  function animate(time: number) {
    if (!startTime) startTime = time;
    const elapsed = time - startTime;
    const progress = Math.min(elapsed / duration, 1);

    const currentExaggeration =
      startExaggeration + progress * (targetExaggeration - startExaggeration);

    const currentPitch =
      startPitch + progress * (targetPitch - startPitch);

    if (targetExaggeration > 0) {
      map.setTerrain({ source: "mapbox-dem", exaggeration: currentExaggeration });
    } else {
      map.setTerrain(
        progress < 1
          ? { source: "mapbox-dem", exaggeration: currentExaggeration }
          : null
      );
    }

    map.setPitch(currentPitch);

    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }

  requestAnimationFrame(animate);
}

export function enable3D(map: mapboxgl.Map) {
  if (!map.getSource("mapbox-dem")) {
    map.addSource("mapbox-dem", {
      type: "raster-dem",
      url: "mapbox://mapbox.terrain-rgb",
      tileSize: 512,
      maxzoom: 14,
    } as any);
  }

  const startPitch = map.getPitch();
  animateTerrain(map, 0, 1.5, startPitch, 70, 1000);
}

export function disable3D(map: mapboxgl.Map) {
  const terrain = map.getTerrain();
  const startExaggeration = (terrain ? terrain.exaggeration as number : 0);
  const startPitch = map.getPitch();

  animateTerrain(map, startExaggeration, 0, startPitch, 0, 1000);
}
