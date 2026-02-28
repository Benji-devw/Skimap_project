import mapboxgl from "mapbox-gl";

// Variable globale pour stocker le popup actif
let snowPopup: mapboxgl.Popup | null = null;

// Fonctions de gestion des événements (stockées pour pouvoir les retirer)
let mouseMoveHandler: ((e: mapboxgl.MapMouseEvent) => void) | null = null;
let mouseLeaveHandler: (() => void) | null = null;

/**
 * Ajoute la couche de neige sur la carte Mapbox
 * Charge le GeoJSON depuis l'API et affiche les polygones colorés
 *
 * @param map - Instance de la carte Mapbox
 */
export async function renderSnowLayer(
  map: mapboxgl.Map,
  stationId?: number,
): Promise<void> {
  try {
    // Charger les données de neige depuis l'API
    const url = stationId
      ? `${import.meta.env.VITE_API_URL}/api/snow-coverage/?station_id=${stationId}`
      : `${import.meta.env.VITE_API_URL}/api/snow-coverage/`;
    const response = await fetch(url);

    if (!response.ok) {
      console.error("Failed to load snow coverage data");
      return;
    }

    const geojson = await response.json();

    // Vérifier si la source existe déjà
    if (map.getSource("snow-coverage")) {
      // Mettre à jour les données
      (map.getSource("snow-coverage") as mapboxgl.GeoJSONSource).setData(
        geojson,
      );
      return;
    }

    // Ajouter la source GeoJSON
    map.addSource("snow-coverage", {
      type: "geojson",
      data: geojson,
    });

    // Ajouter une couche de remplissage (polygones)
    map.addLayer(
      {
        id: "snow-coverage-fill",
        type: "fill",
        source: "snow-coverage",
        paint: {
          "fill-color": ["get", "color"], // Utilise la propriété 'color' de chaque feature
          "fill-opacity": 0.6,
        },
      },
      // Insérer sous les pistes et markers
      "pistes-line",
    );

    // Ajouter une couche de contour pour plus de clarté
    map.addLayer(
      {
        id: "snow-coverage-outline",
        type: "line",
        source: "snow-coverage",
        paint: {
          "line-color": "#ffffff",
          "line-width": 1,
          "line-opacity": 0.3,
        },
      },
      "pistes-line",
    );

    // Retirer les anciens event listeners s'ils existent
    if (mouseMoveHandler) {
      map.off("mousemove", "snow-coverage-fill", mouseMoveHandler);
    }
    if (mouseLeaveHandler) {
      map.off("mouseleave", "snow-coverage-fill", mouseLeaveHandler);
    }

    // Créer les nouveaux event handlers
    mouseMoveHandler = (e: mapboxgl.MapMouseEvent) => {
      if (!e.features || e.features.length === 0) return;

      const feature = e.features[0];
      const properties = feature.properties;

      // Changer le curseur
      map.getCanvas().style.cursor = "pointer";

      // Créer le contenu du popup
      const popupContent = `
        <div class="snow-dtm-popup">
          <strong style="color: ${properties?.color || "#000"};">
            ${properties?.name || "Neige"}
          </strong><br/>
          <span>
            ${properties?.snow_range || "N/A"}<br/>
            ${properties?.description || ""}
          </span>
        </div>
      `;

      // Créer le popup seulement s'il n'existe pas déjà
      if (!snowPopup) {
        snowPopup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
        });
      }

      // Mettre à jour la position et le contenu du popup existant
      snowPopup.setLngLat(e.lngLat).setHTML(popupContent).addTo(map);
    };

    mouseLeaveHandler = () => {
      map.getCanvas().style.cursor = "";
      // Retirer le popup
      if (snowPopup) {
        snowPopup.remove();
        snowPopup = null;
      }
    };

    // Ajouter les event listeners
    map.on("mousemove", "snow-coverage-fill", mouseMoveHandler);
    map.on("mouseleave", "snow-coverage-fill", mouseLeaveHandler);

    console.log("✅ Snow coverage layer added successfully");
  } catch (error) {
    console.error("Error loading snow coverage layer:", error);
  }
}

/**
 * Retire la couche de neige de la carte
 *
 * @param map - Instance de la carte Mapbox
 */
export function removeSnowLayer(map: mapboxgl.Map): void {
  // Retirer le popup s'il existe
  if (snowPopup) {
    snowPopup.remove();
    snowPopup = null;
  }

  // Retirer les event listeners
  if (mouseMoveHandler && map.getLayer("snow-coverage-fill")) {
    map.off("mousemove", "snow-coverage-fill", mouseMoveHandler);
    mouseMoveHandler = null;
  }
  if (mouseLeaveHandler && map.getLayer("snow-coverage-fill")) {
    map.off("mouseleave", "snow-coverage-fill", mouseLeaveHandler);
    mouseLeaveHandler = null;
  }

  // Retirer les layers
  if (map.getLayer("snow-coverage-fill")) {
    map.removeLayer("snow-coverage-fill");
  }
  if (map.getLayer("snow-coverage-outline")) {
    map.removeLayer("snow-coverage-outline");
  }

  // Retirer la source
  if (map.getSource("snow-coverage")) {
    map.removeSource("snow-coverage");
  }

  console.log("❄️ Snow coverage layer removed");
}

/**
 * Toggle la visibilité de la couche de neige
 *
 * @param map - Instance de la carte Mapbox
 * @param visible - true pour afficher, false pour cacher
 */
export function toggleSnowLayerVisibility(
  map: mapboxgl.Map,
  visible: boolean,
): void {
  const visibility = visible ? "visible" : "none";

  if (map.getLayer("snow-coverage-fill")) {
    map.setLayoutProperty("snow-coverage-fill", "visibility", visibility);
  }
  if (map.getLayer("snow-coverage-outline")) {
    map.setLayoutProperty("snow-coverage-outline", "visibility", visibility);
  }
}

/**
 * Ajuste l'opacité de la couche de neige
 *
 * @param map - Instance de la carte Mapbox
 * @param opacity - Valeur entre 0 (transparent) et 1 (opaque)
 */
export function setSnowLayerOpacity(map: mapboxgl.Map, opacity: number): void {
  if (map.getLayer("snow-coverage-fill")) {
    map.setPaintProperty("snow-coverage-fill", "fill-opacity", opacity);
  }
}

/**
 * Obtient la hauteur de neige à une coordonnée donnée
 *
 * @param lat - Latitude
 * @param lng - Longitude
 * @returns Objet avec les informations de neige ou null
 */
export async function getSnowAtPoint(
  lat: number,
  lng: number,
): Promise<{
  snow_height_cm: number | null;
  category: string;
  color: string;
  range: string;
  description?: string;
} | null> {
  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL}/api/snow-at-point/?lat=${lat}&lng=${lng}`,
    );

    if (!response.ok) {
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching snow data at point:", error);
    return null;
  }
}

/**
 * Fonction de debug pour vérifier l'état des popups
 * À utiliser dans la console du navigateur
 */
export function debugSnowPopups(): void {
  const popups = document.querySelectorAll(".mapboxgl-popup");
  console.log("🔍 Debug Snow Popups:");
  console.log(`  Total popups in DOM: ${popups.length}`);
  console.log(`  snowPopup instance exists: ${snowPopup !== null}`);
  console.log(
    `  Event handlers bound: mousemove=${mouseMoveHandler !== null}, mouseleave=${mouseLeaveHandler !== null}`,
  );

  if (popups.length > 1) {
    console.warn("⚠️  WARNING: Multiple popups detected!");
  } else if (popups.length === 0 && snowPopup) {
    console.warn("⚠️  WARNING: snowPopup exists but no DOM element!");
  } else {
    console.log("✅ Popup state is healthy");
  }
}

// Exposer la fonction de debug globalement (pour la console)
if (typeof window !== "undefined") {
  (
    window as Window & { debugSnowPopups?: typeof debugSnowPopups }
  ).debugSnowPopups = debugSnowPopups;
}
