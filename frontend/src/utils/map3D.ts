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
  map.setTerrain({ source: "mapbox-dem", exaggeration: 1.5 });
  map.easeTo({ pitch: 60, bearing: 20, duration: 1000 });
}

export function disable3D(map: mapboxgl.Map) {
  map.setTerrain(null);
  map.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
}
