#!/usr/bin/env python3
"""
Script pour convertir un raster GeoTIFF en GeoJSON avec contours
Spécifiquement pour la visualisation de la couverture neigeuse sur Mapbox

Usage:
    python convert_raster_to_geojson.py \
        --input media/lidar/snow_prediction_classified.tif \
        --output media/lidar/snow_contours.geojson \
        --simplify 10

Fonctionnalités:
    1. Charge le raster classifié (0-5)
    2. Extrait les contours pour chaque classe
    3. Convertit en polygones GeoJSON
    4. Simplifie les géométries pour Mapbox
    5. Ajoute les propriétés (couleur, nom, hauteur)
    6. Convertit Lambert 93 → WGS84
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_classified_raster(filepath, verbose=True):
    """
    Charge un raster classifié GeoTIFF

    Args:
        filepath: Chemin vers le fichier GeoTIFF
        verbose: Afficher les informations

    Returns:
        Tuple (data, transform, crs)
    """
    try:
        import rasterio
    except ImportError:
        print("❌ rasterio n'est pas installé!")
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
            print(f"   Classes: {np.unique(data[~np.isnan(data)])}")

    return data, transform, crs


def extract_contours(data, transform, verbose=True):
    """
    Extrait les contours de chaque classe du raster

    Args:
        data: Grille de données classifiées
        transform: Transformation affine du raster
        verbose: Afficher les informations

    Returns:
        Liste de features GeoJSON (géométries en coordonnées raster)
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"🗺️  EXTRACTION DES CONTOURS")
        print(f"{'=' * 60}\n")

    try:
        import rasterio.features
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union
    except ImportError:
        print("❌ shapely n'est pas installé!")
        print("Installez avec: pip install shapely")
        sys.exit(1)

    # Définition des catégories de neige
    snow_categories = {
        0: {
            "name": "Pas de neige",
            "color": "#FF0000",
            "range": "0-10 cm",
            "description": "Zones très pentues ou exposées",
        },
        1: {
            "name": "Très peu",
            "color": "#FF6600",
            "range": "10-30 cm",
            "description": "Couverture insuffisante",
        },
        2: {
            "name": "Peu",
            "color": "#FFCC00",
            "range": "30-50 cm",
            "description": "Couverture minimale",
        },
        3: {
            "name": "Moyen",
            "color": "#66FF66",
            "range": "50-80 cm",
            "description": "Bonnes conditions",
        },
        4: {
            "name": "Bon",
            "color": "#00CCFF",
            "range": "80-120 cm",
            "description": "Excellentes conditions",
        },
        5: {
            "name": "Excellent",
            "color": "#FFFFFF",
            "range": ">120 cm",
            "description": "Conditions exceptionnelles",
        },
    }

    features = []

    # Extraire les contours pour chaque classe
    unique_classes = np.unique(data[~np.isnan(data)])

    for class_value in unique_classes:
        class_value = int(class_value)

        if class_value not in snow_categories:
            continue

        if verbose:
            print(
                f"Extraction classe {class_value} - {snow_categories[class_value]['name']}..."
            )

        # Créer un masque pour cette classe
        mask = (data == class_value).astype(np.uint8)

        # Extraire les formes (polygones)
        shapes_gen = rasterio.features.shapes(mask, mask=mask, transform=transform)

        # Convertir en shapely geometries et merger les polygones adjacents
        polygons = []
        for geom, value in shapes_gen:
            if value == 1:  # Seulement les zones de cette classe
                polygons.append(shape(geom))

        if not polygons:
            if verbose:
                print(f"   ⚠️  Aucun polygone trouvé pour cette classe")
            continue

        # Fusionner tous les polygones de cette classe
        if len(polygons) > 1:
            merged = unary_union(polygons)
        else:
            merged = polygons[0]

        # Créer la feature GeoJSON
        category = snow_categories[class_value]

        feature = {
            "type": "Feature",
            "properties": {
                "class": int(class_value),
                "name": category["name"],
                "color": category["color"],
                "snow_range": category["range"],
                "description": category["description"],
                "fill-opacity": 0.6,
            },
            "geometry": mapping(merged),
        }

        features.append(feature)

        if verbose:
            area = merged.area  # En unités du CRS (mètres carrés pour Lambert 93)
            print(
                f"   ✅ {len(polygons)} polygones → 1 feature (aire: {area / 10000:.2f} ha)"
            )

    return features


def simplify_geometries(features, tolerance=10, verbose=True):
    """
    Simplifie les géométries pour réduire la taille et améliorer les performances

    Args:
        features: Liste de features GeoJSON
        tolerance: Tolérance de simplification en mètres
        verbose: Afficher les informations

    Returns:
        Liste de features simplifiées
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"✂️  SIMPLIFICATION DES GÉOMÉTRIES")
        print(f"{'=' * 60}\n")
        print(f"Tolérance: {tolerance} mètres")

    try:
        from shapely.geometry import mapping, shape
    except ImportError:
        return features

    simplified_features = []

    for feature in features:
        geom = shape(feature["geometry"])
        simplified_geom = geom.simplify(tolerance, preserve_topology=True)

        # Calculer la réduction
        original_coords = 0
        simplified_coords = 0

        if hasattr(geom, "geoms"):  # MultiPolygon
            original_coords = sum(len(list(g.exterior.coords)) for g in geom.geoms)
            simplified_coords = sum(
                len(list(g.exterior.coords)) for g in simplified_geom.geoms
            )
        elif hasattr(geom, "exterior"):  # Polygon
            original_coords = len(list(geom.exterior.coords))
            simplified_coords = len(list(simplified_geom.exterior.coords))
        elif hasattr(geom, "coords"):  # LineString or Point
            original_coords = len(list(geom.coords))
            simplified_coords = len(list(simplified_geom.coords))

        simplified_feature = {
            "type": "Feature",
            "properties": feature["properties"],
            "geometry": mapping(simplified_geom),
        }

        simplified_features.append(simplified_feature)

        if verbose and original_coords > 0:
            reduction = (1 - simplified_coords / original_coords) * 100
            print(
                f"   {feature['properties']['name']:12s}: {original_coords:6d} → {simplified_coords:6d} coords ({reduction:5.1f}% réduction)"
            )

    return simplified_features


def transform_to_wgs84(features, source_crs, verbose=True):
    """
    Transforme les coordonnées de Lambert 93 vers WGS84 (pour Mapbox)

    Args:
        features: Liste de features GeoJSON
        source_crs: CRS source (ex: EPSG:2154)
        verbose: Afficher les informations

    Returns:
        Liste de features avec coordonnées WGS84
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"🌍 TRANSFORMATION DES COORDONNÉES")
        print(f"{'=' * 60}\n")
        print(f"Source: {source_crs}")
        print(f"Destination: EPSG:4326 (WGS84 pour Mapbox)")

    try:
        from pyproj import Transformer
        from shapely.geometry import mapping, shape
        from shapely.ops import transform
    except ImportError:
        print("❌ pyproj n'est pas installé!")
        sys.exit(1)

    # Créer le transformateur
    transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)

    transformed_features = []

    for feature in features:
        geom = shape(feature["geometry"])

        # Transformer la géométrie
        transformed_geom = transform(transformer.transform, geom)

        transformed_feature = {
            "type": "Feature",
            "properties": feature["properties"],
            "geometry": mapping(transformed_geom),
        }

        transformed_features.append(transformed_feature)

    if verbose:
        print(f"✅ {len(transformed_features)} features transformées")

    return transformed_features


def save_geojson(features, output_path, verbose=True):
    """
    Sauvegarde les features en fichier GeoJSON

    Args:
        features: Liste de features GeoJSON
        output_path: Chemin du fichier de sortie
        verbose: Afficher les informations
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"💾 SAUVEGARDE DU GEOJSON")
        print(f"{'=' * 60}\n")
        print(f"Fichier de sortie: {output_path}")

    # Créer le dossier de sortie si nécessaire
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Créer le GeoJSON FeatureCollection
    geojson = {"type": "FeatureCollection", "features": features}

    # Sauvegarder
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    if verbose:
        file_size = Path(output_path).stat().st_size / 1024
        print(f"✅ GeoJSON sauvegardé!")
        print(f"📏 Taille du fichier: {file_size:.2f} Ko")
        print(f"📊 Nombre de features: {len(features)}")


def main():
    """Fonction principale"""

    parser = argparse.ArgumentParser(
        description="Convertir un raster GeoTIFF classifié en GeoJSON pour Mapbox"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Chemin vers le fichier GeoTIFF classifié",
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Chemin du fichier GeoJSON de sortie"
    )
    parser.add_argument(
        "--simplify",
        type=float,
        default=10.0,
        help="Tolérance de simplification en mètres (défaut: 10)",
    )
    parser.add_argument(
        "--no-simplify", action="store_true", help="Ne pas simplifier les géométries"
    )
    parser.add_argument("--quiet", action="store_true", help="Mode silencieux")

    args = parser.parse_args()
    verbose = not args.quiet

    if verbose:
        print(f"\n{'#' * 60}")
        print(f"#  CONVERSION RASTER → GEOJSON")
        print(f"{'#' * 60}")

    # Étape 1: Charger le raster
    data, transform, crs = load_classified_raster(args.input, verbose=verbose)

    # Étape 2: Extraire les contours
    features = extract_contours(data, transform, verbose=verbose)

    if not features:
        print("❌ Aucune feature extraite!")
        sys.exit(1)

    # Étape 3: Simplifier les géométries (optionnel)
    if not args.no_simplify:
        features = simplify_geometries(
            features, tolerance=args.simplify, verbose=verbose
        )

    # Étape 4: Transformer en WGS84
    features = transform_to_wgs84(features, crs, verbose=verbose)

    # Étape 5: Sauvegarder
    save_geojson(features, args.output, verbose=verbose)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"✅ CONVERSION TERMINÉE AVEC SUCCÈS!")
        print(f"{'=' * 60}\n")
        print(f"📌 PROCHAINES ÉTAPES:")
        print(f"   1. Vérifier le GeoJSON sur geojson.io")
        print(f"   2. Créer l'API Django pour servir les données")
        print(f"   3. Intégrer dans MapView React")
        print(f"   4. Afficher sur Mapbox avec les bonnes couleurs\n")


if __name__ == "__main__":
    main()
