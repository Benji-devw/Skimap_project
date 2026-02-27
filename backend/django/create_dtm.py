#!/usr/bin/env python3
"""
Script pour créer un Modèle Numérique de Terrain (MNT/DTM) à partir de données LIDAR

Usage:
    python create_dtm.py --input media/lidar/fichier.laz --output media/lidar/dtm.tif --resolution 1.0

Étapes:
    1. Charge le fichier LAZ
    2. Filtre les points de sol (classe 2)
    3. Crée une grille raster par interpolation
    4. Génère un GeoTIFF
    5. Calcule pente et exposition (optionnel)
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from scipy.interpolate import griddata


def load_ground_points(filepath, verbose=True):
    """
    Charge un fichier LAZ et extrait uniquement les points de sol (classe 2)

    Args:
        filepath: Chemin vers le fichier LAZ
        verbose: Afficher les informations de progression

    Returns:
        Tuple (x, y, z) contenant les coordonnées des points de sol
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"📂 CHARGEMENT DU FICHIER LIDAR")
        print(f"{'=' * 60}\n")
        print(f"Fichier: {filepath}")

    try:
        import laspy
    except ImportError:
        print("❌ laspy n'est pas installé!")
        print("Installez avec: pip install laspy")
        sys.exit(1)

    # Vérifier que le fichier existe
    if not Path(filepath).exists():
        print(f"❌ Fichier introuvable: {filepath}")
        sys.exit(1)

    # Charger le fichier
    start_time = time.time()
    las = laspy.read(filepath)
    load_time = time.time() - start_time

    if verbose:
        print(f"✅ Chargé en {load_time:.2f}s")
        print(f"📊 Total de points: {len(las.points):,}")

    # Filtrer les points de sol (classe 2)
    if "classification" not in las.point_format.dimension_names:
        print("❌ Pas de classification disponible dans ce fichier!")
        sys.exit(1)

    ground_mask = las.classification == 2
    ground_count = np.sum(ground_mask)

    if ground_count == 0:
        print("❌ Aucun point de sol (classe 2) trouvé!")
        sys.exit(1)

    if verbose:
        percentage = (ground_count / len(las.points)) * 100
        print(f"🌍 Points de sol (classe 2): {ground_count:,} ({percentage:.1f}%)")

    # Extraire les coordonnées X, Y, Z des points de sol
    x = las.x[ground_mask]
    y = las.y[ground_mask]
    z = las.z[ground_mask]

    if verbose:
        print(f"\n📍 Emprise du terrain:")
        print(
            f"   X: {np.min(x):.2f} → {np.max(x):.2f} ({np.max(x) - np.min(x):.2f} m)"
        )
        print(
            f"   Y: {np.min(y):.2f} → {np.max(y):.2f} ({np.max(y) - np.min(y):.2f} m)"
        )
        print(
            f"   Z: {np.min(z):.2f} → {np.max(z):.2f} m (dénivelé: {np.max(z) - np.min(z):.2f} m)"
        )

    return x, y, z, las.header


def create_grid(x, y, z, resolution=1.0, method="linear", verbose=True):
    """
    Crée une grille raster régulière à partir de points 3D dispersés

    Args:
        x, y, z: Coordonnées des points
        resolution: Résolution de la grille en mètres (ex: 1.0 = 1m x 1m par pixel)
        method: Méthode d'interpolation ('linear', 'nearest', 'cubic')
        verbose: Afficher les informations

    Returns:
        Tuple (grid, grid_x, grid_y) contenant la grille d'altitude et les coordonnées
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"🗺️  CRÉATION DE LA GRILLE RASTER")
        print(f"{'=' * 60}\n")
        print(f"Résolution: {resolution} m/pixel")
        print(f"Méthode d'interpolation: {method}")

    # Définir l'emprise de la grille
    x_min, x_max = np.min(x), np.max(x)
    y_min, y_max = np.min(y), np.max(y)

    # Créer les axes de la grille
    grid_x = np.arange(x_min, x_max, resolution)
    grid_y = np.arange(y_min, y_max, resolution)

    # Créer la grille 2D
    grid_x_mesh, grid_y_mesh = np.meshgrid(grid_x, grid_y)

    grid_shape = grid_x_mesh.shape
    n_pixels = grid_shape[0] * grid_shape[1]

    if verbose:
        print(f"Dimensions de la grille: {grid_shape[1]} x {grid_shape[0]} pixels")
        print(f"Nombre total de pixels: {n_pixels:,}")
        print(f"Taille approximative: {(n_pixels * 4) / (1024**2):.2f} Mo (float32)")

    # Interpolation
    if verbose:
        print(f"\n⏳ Interpolation en cours...")
        start_time = time.time()

    # Préparer les points source
    points = np.column_stack((x, y))

    # Interpoler sur la grille
    # Note: griddata peut être lent pour beaucoup de points
    # Pour de meilleures performances, considérez scipy.interpolate.RBFInterpolator
    grid = griddata(
        points, z, (grid_x_mesh, grid_y_mesh), method=method, fill_value=np.nan
    )

    if verbose:
        interp_time = time.time() - start_time
        print(f"✅ Interpolation terminée en {interp_time:.2f}s")

        # Statistiques sur la grille
        valid_pixels = np.sum(~np.isnan(grid))
        print(f"\n📊 Statistiques de la grille:")
        print(
            f"   Pixels valides: {valid_pixels:,} ({valid_pixels / n_pixels * 100:.1f}%)"
        )
        print(f"   Altitude min: {np.nanmin(grid):.2f} m")
        print(f"   Altitude max: {np.nanmax(grid):.2f} m")
        print(f"   Altitude moyenne: {np.nanmean(grid):.2f} m")

    return grid, grid_x, grid_y


def save_geotiff(grid, grid_x, grid_y, output_path, crs="EPSG:2154", verbose=True):
    """
    Sauvegarde la grille en tant que GeoTIFF

    Args:
        grid: Grille d'altitude (numpy array 2D)
        grid_x, grid_y: Coordonnées de la grille
        output_path: Chemin de sortie du fichier GeoTIFF
        crs: Système de coordonnées (par défaut Lambert 93)
        verbose: Afficher les informations
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"💾 SAUVEGARDE DU GEOTIFF")
        print(f"{'=' * 60}\n")
        print(f"Fichier de sortie: {output_path}")

    try:
        import rasterio
        from rasterio.transform import from_origin
    except ImportError:
        print("❌ rasterio n'est pas installé!")
        print("Installez avec: pip install rasterio")
        sys.exit(1)

    # Créer le dossier de sortie si nécessaire
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Calculer la transformation affine
    resolution = grid_x[1] - grid_x[0]
    transform = from_origin(grid_x[0], grid_y[-1], resolution, resolution)

    # Créer le fichier GeoTIFF
    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=grid.shape[0],
        width=grid.shape[1],
        count=1,
        dtype=grid.dtype,
        crs=crs,
        transform=transform,
        compress="lzw",  # Compression pour réduire la taille du fichier
        nodata=np.nan,
    ) as dst:
        dst.write(grid, 1)

    if verbose:
        file_size = Path(output_path).stat().st_size / (1024**2)
        print(f"✅ GeoTIFF sauvegardé!")
        print(f"📏 Taille du fichier: {file_size:.2f} Mo")
        print(f"🌍 CRS: {crs}")


def calculate_slope_aspect(grid, resolution, verbose=True):
    """
    Calcule la pente et l'exposition à partir d'un MNT

    Args:
        grid: Grille d'altitude (numpy array 2D)
        resolution: Résolution de la grille en mètres
        verbose: Afficher les informations

    Returns:
        Tuple (slope, aspect) en degrés
    """
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"📐 CALCUL DE LA PENTE ET DE L'EXPOSITION")
        print(f"{'=' * 60}\n")

    # Calculer les gradients
    dy, dx = np.gradient(grid, resolution)

    # Pente en degrés
    slope = np.degrees(np.arctan(np.sqrt(dx**2 + dy**2)))

    # Exposition (aspect) en degrés (0 = Nord, 90 = Est, 180 = Sud, 270 = Ouest)
    aspect = np.degrees(np.arctan2(-dx, dy))
    aspect = (aspect + 360) % 360  # Normaliser entre 0 et 360

    if verbose:
        print(f"📊 Statistiques de pente:")
        print(f"   Pente min: {np.nanmin(slope):.2f}°")
        print(f"   Pente max: {np.nanmax(slope):.2f}°")
        print(f"   Pente moyenne: {np.nanmean(slope):.2f}°")
        print(f"\n🧭 Statistiques d'exposition:")
        print(f"   Exposition moyenne: {np.nanmean(aspect):.2f}°")

    return slope, aspect


def main():
    """Fonction principale"""

    parser = argparse.ArgumentParser(
        description="Créer un Modèle Numérique de Terrain (MNT) à partir de données LIDAR"
    )
    parser.add_argument(
        "--input", type=str, required=True, help="Chemin vers le fichier LAZ d'entrée"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Chemin du fichier GeoTIFF de sortie"
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=1.0,
        help="Résolution de la grille en mètres (défaut: 1.0)",
    )
    parser.add_argument(
        "--method",
        type=str,
        default="linear",
        choices=["linear", "nearest", "cubic"],
        help="Méthode d'interpolation (défaut: linear)",
    )
    parser.add_argument(
        "--crs",
        type=str,
        default="EPSG:2154",
        help="Système de coordonnées (défaut: EPSG:2154 = Lambert 93)",
    )
    parser.add_argument(
        "--calculate-slope",
        action="store_true",
        help="Calculer et sauvegarder la pente",
    )
    parser.add_argument(
        "--calculate-aspect",
        action="store_true",
        help="Calculer et sauvegarder l'exposition",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Mode silencieux (pas de sortie verbose)"
    )

    args = parser.parse_args()
    verbose = not args.quiet

    if verbose:
        print(f"\n{'#' * 60}")
        print(f"#  GÉNÉRATION DE MODÈLE NUMÉRIQUE DE TERRAIN (MNT)")
        print(f"{'#' * 60}")

    # Étape 1: Charger les points de sol
    x, y, z, header = load_ground_points(args.input, verbose=verbose)

    # Étape 2: Créer la grille raster
    grid, grid_x, grid_y = create_grid(
        x, y, z, resolution=args.resolution, method=args.method, verbose=verbose
    )

    # Étape 3: Sauvegarder le GeoTIFF
    save_geotiff(grid, grid_x, grid_y, args.output, crs=args.crs, verbose=verbose)

    # Étape 4: Calculer pente et exposition si demandé
    if args.calculate_slope or args.calculate_aspect:
        slope, aspect = calculate_slope_aspect(grid, args.resolution, verbose=verbose)

        if args.calculate_slope:
            slope_output = args.output.replace(".tif", "_slope.tif")
            save_geotiff(
                slope, grid_x, grid_y, slope_output, crs=args.crs, verbose=verbose
            )
            if verbose:
                print(f"✅ Pente sauvegardée: {slope_output}")

        if args.calculate_aspect:
            aspect_output = args.output.replace(".tif", "_aspect.tif")
            save_geotiff(
                aspect, grid_x, grid_y, aspect_output, crs=args.crs, verbose=verbose
            )
            if verbose:
                print(f"✅ Exposition sauvegardée: {aspect_output}")

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"✅ TRAITEMENT TERMINÉ AVEC SUCCÈS!")
        print(f"{'=' * 60}\n")
        print(f"📌 PROCHAINES ÉTAPES:")
        print(f"   1. Visualiser le MNT avec QGIS ou un autre SIG")
        print(f"   2. Convertir en tuiles pour Mapbox (mapbox-tilesets)")
        print(f"   3. Intégrer dans votre carte web")
        print(f"   4. Combiner avec les données de neige\n")


if __name__ == "__main__":
    main()
