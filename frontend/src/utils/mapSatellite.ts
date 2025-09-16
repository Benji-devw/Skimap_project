import mapboxgl from "mapbox-gl";

export function enableSatellite(map: mapboxgl.Map) {
  map.setStyle("mapbox://styles/mapbox/satellite-streets-v12");
}

export function disableSatellite(map: mapboxgl.Map) {
  map.setStyle("mapbox://styles/mapbox/streets-v12");
}