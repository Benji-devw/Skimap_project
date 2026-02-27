#!/usr/bin/env python3
"""
Script pour prédire l'accumulation de neige en combinant :
- Modèle Numérique de Terrain (MNT) - altitude
- Pente (slope) - où la neige glisse ou s'accumule
- Exposition (aspect) - ensoleillement et fonte
- Open-Meteo API - hauteur de neige réelle en temps réel (calibration automatique)

Usage:
    # Avec récupération automatique depuis Open-Meteo (recommandé)
    python predict_snow_coverage.py \
        --dtm media/lidar/dtm_coste_belle.tif \
        --slope media/lidar/dtm_coste_belle_slope.tif \
        --aspect media/lidar/dtm_coste_belle_aspect.tif \
        --output media/lidar/snow_prediction.tif \
        --lat 44.602 --lon 6.220

    # Avec une valeur manuelle (fallback)
    python predict_snow_coverage.py \
        --dtm media/lidar/dtm_coste_belle.tif \
        --slope media/lidar/dtm_coste_belle_slope.tif \
        --aspect media/lidar/dtm_coste_belle_aspect.tif \
        --output media/lidar/snow_prediction.tif \
        --base-snow 75

Le modèle d'accumulation prend en compte :
    - Altitude : +1 cm de neige par 100m d'altitude
    - Pente : Réduction si > 35° (neige glisse)
    - Exposition : Réduction au sud (fonte solaire)
    - Vent : Réduction sur crêtes exposées
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

# ─── Récupération Open-Meteo ─────────────────────────────────────────────────


def fetch_base_snow_from_open_meteo(
    lat: float, lon: float, verbose: bool = True
) -> float | None:
    """
    Récupère la hauteur de neige actuelle depuis Open-Meteo pour une coordonnée.
    Open-Meteo est gratuit et ne nécessite pas de clé API.

    Args:
        lat: Latitude WGS84
        lon: Longitude WGS84
        verbose: Afficher les logs

    Returns:
        Hauteur de neige en cm, ou None si indisponible
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "snow_depth",
        "timezone": "UTC",
        "forecast_days": 1,
    }
    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"

    if verbose:
        print(f"\n🌐 Récupération Open-Meteo...")
        print(f"   URL : {url}")

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"⚠️  Impossible de joindre Open-Meteo : {exc}")
        return None

    hourly = data.get("hourly", {})
    snow_depths = hourly.get("snow_depth", [])
    times = hourly.get("time", [])

    if not snow_depths:
        if verbose:
            print("⚠️  Open-Meteo n'a pas retourné de donnée snow_depth")
        return None

    # Trouver l'index de l'heure courante UTC
    from datetime import datetime, timezone

    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:00")
    current_idx = len(times) - 1
    for i, t in enumerate(times):
        if t == now_str:
            current_idx = i
            break

    # Chercher en arrière le dernier index non-None
    snow_m = None
    for i in range(current_idx, -1, -1):
        if snow_depths[i] is not None:
            snow_m = snow_depths[i]
            break

    if snow_m is None:
        if verbose:
            print("⚠️  Toutes les valeurs snow_depth sont None")
        return None

    # Open-Meteo retourne snow_depth en mètres → convertir en cm
    snow_cm = round(snow_m * 100, 1)

    if verbose:
        matched_time = times[current_idx] if times else "?"
        print(f"   ✅ Heure de référence : {matched_time} UTC")
        print(f"   ❄️  Hauteur de neige   : {snow_m} m → {snow_cm} cm")

    return snow_cm


def load_raster(filepath, verbose=True):
    """
    Charge un fichier GeoTIFF

    Args:
        filepath: Chemin vers le fichier GeoTIFF
        verbose: Afficher les informations

    Returns:
        Tuple (data, transform, crs) du raster
    """
    try:
        import rasterio
    except ImportError:
        print("❌ rasterio n'est pas installé!")
        print("Installez avec: pip install rasterio")
        sys.exit(1)

    if not Path(filepath).exists():
        print(f"❌ Fichier introuvable: {filepath}")
        sys.exit(1)

    with rasterio.open(filepath) as src:
        data = src.read(1)
        transform = src.transform
        crs = src.crs

        if verbose:
            print(f"✅ Chargé: {Path(filepath).name}")
            print(f"   Dimensions: {data.shape[1]} x {data.shape[0]} pixels")
            print(f"   Min: {np.nanmin(data):.2f}, Max: {np.nanmax(data):.2f}")

    return data, transform, crs


def calculate_altitude_factor(elevation, base_elevation=1500):
    """
    Calcule le facteur d'altitude pour l'accumulation de neige
    Règle : +1 cm de neige par 100m d'altitude au-dessus de la base

    Args:
        elevation: Grille d'altitude (numpy array)
        base_elevation: Altitude de référence en mètres

    Returns:
        Facteur multiplicateur (1.0 = pas de changement)
    """
    # Différence d'altitude par rapport à la base
    altitude_diff = elevation - base_elevation

    # +10% de neige par 100m d'altitude
    # Exemple: à 1600m (100m plus haut) = 10% de neige en plus
    factor = 1.0 + (altitude_diff / 1000.0)

    # Limiter le facteur entre 0.5 et 2.0
    factor = np.clip(factor, 0.5, 2.0)

    return factor


def calculate_slope_factor(slope):
    """
    Calcule le facteur de pente pour l'accumulation de neige

    Logique :
    - Pente < 25° : Accumulation normale (facteur = 1.0)
    - Pente 25-35° : Accumulation réduite progressivement
    - Pente 35-45° : Forte réduction (risque d'avalanche)
    - Pente > 45° : Très peu de neige reste (facteur = 0.2)

    Args:
        slope: Grille de pente en degrés (numpy array)

    Returns:
        Facteur multiplicateur (0.0 - 1.0)
    """
    factor = np.ones_like(slope)

    # Pente modérée (25-35°) : réduction progressive
    mask_moderate = (slope >= 25) & (slope < 35)
    factor[mask_moderate] = 1.0 - ((slope[mask_moderate] - 25) / 10) * 0.3

    # Pente forte (35-45°) : forte réduction
    mask_steep = (slope >= 35) & (slope < 45)
    factor[mask_steep] = 0.7 - ((slope[mask_steep] - 35) / 10) * 0.4

    # Pente très forte (> 45°) : presque pas de neige
    mask_very_steep = slope >= 45
    factor[mask_very_steep] = 0.2 - ((slope[mask_very_steep] - 45) / 30) * 0.15
    factor[mask_very_steep] = np.clip(factor[mask_very_steep], 0.05, 0.2)

    return factor


def calculate_aspect_factor(aspect):
    """
    Calcule le facteur d'exposition pour l'accumulation de neige

    Logique :
    - Nord (0°, 360°) : Meilleure conservation (facteur = 1.2)
    - Nord-Est / Nord-Ouest : Bonne conservation (facteur = 1.1)
    - Est / Ouest : Neutre (facteur = 1.0)
    - Sud-Est / Sud-Ouest : Fonte plus rapide (facteur = 0.85)
    - Sud (180°) : Forte fonte (facteur = 0.7)

    Args:
        aspect: Grille d'exposition en degrés (0-360, 0=Nord)

    Returns:
        Facteur multiplicateur (0.7 - 1.2)
    """
    # Normaliser l'aspect pour que 0° soit au sud (pour le calcul)
    # On veut que cos(0) = -1 au sud et cos(180) = 1 au nord
    aspect_rad = np.radians((aspect + 180) % 360)

    # Calculer un facteur basé sur le cosinus
    # cos(0°) = 1 (nord) → facteur élevé
    # cos(180°) = -1 (sud) → facteur réduit
    cos_aspect = np.cos(aspect_rad)

    # Transformer en facteur entre 0.7 (sud) et 1.2 (nord)
    # cos varie de -1 à 1, on le transforme en 0.7 à 1.2
    factor = 0.95 + (cos_aspect * 0.25)

    return factor


def calculate_wind_exposure_factor(elevation, slope):
    """
    Calcule le facteur d'exposition au vent
    Les crêtes et sommets exposés perdent de la neige à cause du vent

    Logique :
    - Points hauts + faible pente = crête exposée (facteur réduit)
    - Points bas ou forte pente = protégé du vent (facteur normal)

    Args:
        elevation: Grille d'altitude
        slope: Grille de pente en degrés

    Returns:
        Facteur multiplicateur (0.6 - 1.0)
    """
    # Normaliser l'élévation entre 0 et 1
    elev_normalized = (elevation - np.nanmin(elevation)) / (
        np.nanmax(elevation) - np.nanmin(elevation)
    )

    # Les crêtes sont des zones hautes avec faible pente
    # Identifier les zones de crête : altitude > 75e percentile ET pente < 20°
    is_ridge = (elev_normalized > 0.75) & (slope < 20)

    factor = np.ones_like(elevation)

    # Réduire l'accumulation sur les crêtes (vent fort)
    factor[is_ridge] = 0.6

    # Zones moyennement exposées (altitude élevée mais pas crête)
    is_upper = (elev_normalized > 0.6) & (~is_ridge)
    factor[is_upper] = 0.85

    return factor


def predict_snow_accumulation(
    elevation, slope, aspect, base_snow_cm=75, base_elevation=1500, verbose=True
):
    """
    Prédit l'accumulation de neige en combinant tous les facteurs

    Args:
        elevation: Grille d'altitude (numpy array)
        slope: Grille de pente en degrés
        aspect: Grille d'exposition en degrés
        base_snow_cm: Hauteur de neige de base en cm (mesure station)
        base_elevation: Altitude de référence pour les mesures
        verbose: Afficher les informations

    Returns:
        Grille de hauteur de neige prédite en cm
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"🧮 CALCUL DU MODÈLE D'ACCUMULATION DE NEIGE")
        print(f"{'=' * 60}\n")
        print(f"Neige de base: {base_snow_cm} cm (altitude {base_elevation}m)")

    # Calculer chaque facteur
    altitude_factor = calculate_altitude_factor(elevation, base_elevation)
    slope_factor = calculate_slope_factor(slope)
    aspect_factor = calculate_aspect_factor(aspect)
    wind_factor = calculate_wind_exposure_factor(elevation, slope)

    if verbose:
        print(f"\n📊 Facteurs calculés:")
        print(
            f"   Altitude: {np.nanmean(altitude_factor):.3f} (min={np.nanmin(altitude_factor):.3f}, max={np.nanmax(altitude_factor):.3f})"
        )
        print(
            f"   Pente:    {np.nanmean(slope_factor):.3f} (min={np.nanmin(slope_factor):.3f}, max={np.nanmax(slope_factor):.3f})"
        )
        print(
            f"   Exposition: {np.nanmean(aspect_factor):.3f} (min={np.nanmin(aspect_factor):.3f}, max={np.nanmax(aspect_factor):.3f})"
        )
        print(
            f"   Vent:     {np.nanmean(wind_factor):.3f} (min={np.nanmin(wind_factor):.3f}, max={np.nanmax(wind_factor):.3f})"
        )

    # Combiner tous les facteurs
    combined_factor = altitude_factor * slope_factor * aspect_factor * wind_factor

    # Calculer la hauteur de neige prédite
    predicted_snow = base_snow_cm * combined_factor

    # Assurer que la neige ne soit pas négative
    predicted_snow = np.maximum(predicted_snow, 0)

    if verbose:
        print(f"\n❄️  RÉSULTAT DE LA PRÉDICTION:")
        print(f"   Neige min: {np.nanmin(predicted_snow):.1f} cm")
        print(f"   Neige max: {np.nanmax(predicted_snow):.1f} cm")
        print(f"   Neige moyenne: {np.nanmean(predicted_snow):.1f} cm")
        print(f"   Écart-type: {np.nanstd(predicted_snow):.1f} cm")

    return predicted_snow


def save_snow_prediction(snow_grid, transform, crs, output_path, verbose=True):
    """
    Sauvegarde la prédiction de neige en GeoTIFF

    Args:
        snow_grid: Grille de hauteur de neige prédite
        transform: Transformation affine du raster
        crs: Système de coordonnées
        output_path: Chemin de sortie
        verbose: Afficher les informations
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"💾 SAUVEGARDE DE LA PRÉDICTION")
        print(f"{'=' * 60}\n")
        print(f"Fichier de sortie: {output_path}")

    try:
        import rasterio
    except ImportError:
        print("❌ rasterio n'est pas installé!")
        sys.exit(1)

    # Créer le dossier de sortie si nécessaire
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Sauvegarder le GeoTIFF
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=snow_grid.shape[0],
        width=snow_grid.shape[1],
        count=1,
        dtype=snow_grid.dtype,
        crs=crs,
        transform=transform,
        compress="lzw",
        nodata=np.nan,
    ) as dst:
        dst.write(snow_grid, 1)

    if verbose:
        file_size = Path(output_path).stat().st_size / (1024**2)
        print(f"✅ Prédiction sauvegardée!")
        print(f"📏 Taille du fichier: {file_size:.2f} Mo")


def create_color_classification(snow_grid, verbose=True):
    """
    Classifie la neige en catégories de couleur pour visualisation

    Args:
        snow_grid: Grille de hauteur de neige
        verbose: Afficher les informations

    Returns:
        Grille classifiée (0-5) et dictionnaire de couleurs
    """
    # Classification :
    # 0 = Pas de neige (0-10 cm) → Rouge
    # 1 = Très peu (10-30 cm) → Orange
    # 2 = Peu (30-50 cm) → Jaune
    # 3 = Moyen (50-80 cm) → Vert clair
    # 4 = Bon (80-120 cm) → Bleu
    # 5 = Excellent (>120 cm) → Blanc

    classified = np.zeros_like(snow_grid, dtype=np.uint8)

    classified[snow_grid < 10] = 0
    classified[(snow_grid >= 10) & (snow_grid < 30)] = 1
    classified[(snow_grid >= 30) & (snow_grid < 50)] = 2
    classified[(snow_grid >= 50) & (snow_grid < 80)] = 3
    classified[(snow_grid >= 80) & (snow_grid < 120)] = 4
    classified[snow_grid >= 120] = 5

    color_map = {
        0: {"name": "Pas de neige", "color": "#FF0000", "range": "0-10 cm"},
        1: {"name": "Très peu", "color": "#FF6600", "range": "10-30 cm"},
        2: {"name": "Peu", "color": "#FFCC00", "range": "30-50 cm"},
        3: {"name": "Moyen", "color": "#66FF66", "range": "50-80 cm"},
        4: {"name": "Bon", "color": "#00CCFF", "range": "80-120 cm"},
        5: {"name": "Excellent", "color": "#FFFFFF", "range": ">120 cm"},
    }

    if verbose:
        print(f"\n🎨 CLASSIFICATION PAR COULEUR:")
        print(f"{'-' * 60}")
        for cls, info in color_map.items():
            count = np.sum(classified == cls)
            percentage = (count / classified.size) * 100
            print(
                f"   {cls} - {info['name']:12s} ({info['range']:12s}): {count:8,} pixels ({percentage:5.1f}%)"
            )

    return classified, color_map


def main():
    """Fonction principale"""

    parser = argparse.ArgumentParser(
        description="Prédire l'accumulation de neige à partir du MNT, pente et exposition"
    )
    parser.add_argument(
        "--dtm",
        type=str,
        required=True,
        help="Chemin vers le fichier MNT (DTM) GeoTIFF",
    )
    parser.add_argument(
        "--slope",
        type=str,
        required=True,
        help="Chemin vers le fichier de pente GeoTIFF",
    )
    parser.add_argument(
        "--aspect",
        type=str,
        required=True,
        help="Chemin vers le fichier d'exposition GeoTIFF",
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Chemin du fichier de sortie GeoTIFF"
    )
    parser.add_argument(
        "--base-snow",
        type=float,
        default=None,
        help="Hauteur de neige de base en cm (si non fourni, récupérée depuis Open-Meteo via --lat/--lon)",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=None,
        help="Latitude WGS84 de la station (pour récupérer la neige depuis Open-Meteo)",
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=None,
        help="Longitude WGS84 de la station (pour récupérer la neige depuis Open-Meteo)",
    )
    parser.add_argument(
        "--base-elevation",
        type=float,
        default=1500.0,
        help="Altitude de référence en mètres (défaut: 1500)",
    )
    parser.add_argument(
        "--save-classified",
        action="store_true",
        help="Sauvegarder aussi la version classifiée par couleur",
    )
    parser.add_argument("--quiet", action="store_true", help="Mode silencieux")

    args = parser.parse_args()
    verbose = not args.quiet

    if verbose:
        print(f"\n{'#' * 60}")
        print(f"#  PRÉDICTION D'ACCUMULATION DE NEIGE")
        print(f"{'#' * 60}")

    # ── Résolution du base_snow ──────────────────────────────────────────────
    base_snow_cm = args.base_snow

    if base_snow_cm is None:
        # Essayer Open-Meteo si lat/lon fournis
        if args.lat is not None and args.lon is not None:
            if verbose:
                print(f"\n📡 SOURCE : Open-Meteo (lat={args.lat}, lon={args.lon})")
            base_snow_cm = fetch_base_snow_from_open_meteo(
                args.lat, args.lon, verbose=verbose
            )
            if base_snow_cm is None:
                print("⚠️  Open-Meteo indisponible, fallback sur 75 cm")
                base_snow_cm = 75.0
        else:
            print(
                "⚠️  Ni --base-snow ni --lat/--lon fournis. "
                "Utilisation de la valeur par défaut : 75 cm\n"
                "    → Fournissez --lat et --lon pour des données réelles."
            )
            base_snow_cm = 75.0
    else:
        if verbose:
            print(f"\n📋 SOURCE : valeur manuelle (--base-snow {base_snow_cm} cm)")

    if verbose:
        print(f"\n❄️  Hauteur de neige de référence : {base_snow_cm} cm")

    # Charger les rasters
    if verbose:
        print(f"\n📂 CHARGEMENT DES DONNÉES")
        print(f"{'-' * 60}")

    elevation, transform, crs = load_raster(args.dtm, verbose=verbose)
    slope, _, _ = load_raster(args.slope, verbose=verbose)
    aspect, _, _ = load_raster(args.aspect, verbose=verbose)

    # Vérifier que les dimensions correspondent
    if not (elevation.shape == slope.shape == aspect.shape):
        print("❌ Erreur: Les dimensions des rasters ne correspondent pas!")
        sys.exit(1)

    # Calculer la prédiction
    predicted_snow = predict_snow_accumulation(
        elevation,
        slope,
        aspect,
        base_snow_cm=base_snow_cm,
        base_elevation=args.base_elevation,
        verbose=verbose,
    )

    # Sauvegarder le résultat
    save_snow_prediction(predicted_snow, transform, crs, args.output, verbose=verbose)

    # Créer et sauvegarder la version classifiée si demandé
    if args.save_classified:
        classified, color_map = create_color_classification(
            predicted_snow, verbose=verbose
        )

        classified_output = args.output.replace(".tif", "_classified.tif")
        save_snow_prediction(
            classified.astype(np.float32),
            transform,
            crs,
            classified_output,
            verbose=verbose,
        )

        if verbose:
            print(f"✅ Version classifiée sauvegardée: {classified_output}")

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"✅ PRÉDICTION TERMINÉE AVEC SUCCÈS!")
        print(f"{'=' * 60}\n")
        print(f"📌 PROCHAINES ÉTAPES:")
        print(f"   1. Visualiser le résultat avec QGIS")
        print(f"   2. Convertir en format compatible Mapbox")
        print(f"   3. Créer une API pour servir les données")
        print(f"   4. Afficher la couche sur votre carte web\n")


if __name__ == "__main__":
    main()
