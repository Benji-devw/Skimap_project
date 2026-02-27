"""
Commande Django pour mettre à jour automatiquement la carte de neige.

Pipeline complet :
    1. Récupère la hauteur de neige réelle depuis Open-Meteo
    2. Lance predict_snow_coverage.py avec cette valeur réelle
    3. Lance convert_raster_to_geojson.py pour régénérer le GeoJSON
    4. Sauvegarde la mesure en base (SnowMeasure)

Usage :
    python manage.py update_snow_map
    python manage.py update_snow_map --station-id 1
    python manage.py update_snow_map --dry-run
"""

import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from stations.models import SnowMeasure, Station
from stations.services.open_meteo import fetch_snow_for_station

# Chemins des fichiers LIDAR (relatifs à /app)
BASE_DIR = Path("/app")
MEDIA_LIDAR = BASE_DIR / "media" / "lidar"

# Station associée au fichier LAZ disponible
LIDAR_STATION_ID = 3  # Ancelle — le LAZ couvre son domaine skiable (Coste Belle)

# Fichiers DTM attendus (générés par create_dtm.py)
DTM_FILE = MEDIA_LIDAR / "dtm_coste_belle.tif"
SLOPE_FILE = MEDIA_LIDAR / "dtm_coste_belle_slope.tif"
ASPECT_FILE = MEDIA_LIDAR / "dtm_coste_belle_aspect.tif"

# Fichiers de sortie
SNOW_PREDICTION_FILE = MEDIA_LIDAR / "snow_prediction.tif"
SNOW_CLASSIFIED_FILE = MEDIA_LIDAR / "snow_prediction_classified.tif"
SNOW_GEOJSON_FILE = MEDIA_LIDAR / "snow_contours.geojson"

# Scripts de traitement
PREDICT_SCRIPT = BASE_DIR / "predict_snow_coverage.py"
CONVERT_SCRIPT = BASE_DIR / "convert_raster_to_geojson.py"


class Command(BaseCommand):
    help = "Met à jour la carte de neige : Open-Meteo → prédiction LIDAR → GeoJSON → DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--station-id",
            type=int,
            default=LIDAR_STATION_ID,
            help=f"ID de la station à utiliser pour Open-Meteo (défaut : {LIDAR_STATION_ID} = Ancelle)",
        )
        parser.add_argument(
            "--base-elevation",
            type=float,
            default=1600.0,
            help="Altitude de référence en mètres pour le modèle (défaut : 1600)",
        )
        parser.add_argument(
            "--simplify",
            type=float,
            default=10.0,
            help="Tolérance de simplification GeoJSON en mètres (défaut : 10)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait fait sans exécuter les scripts ni sauvegarder",
        )

    def handle(self, *args, **options):
        station_id = options["station_id"]
        base_elevation = options["base_elevation"]
        simplify = options["simplify"]
        dry_run = options["dry_run"]

        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("🗺️  MISE À JOUR DE LA CARTE DE NEIGE")
        self.stdout.write(f"    {timezone.now().strftime('%Y-%m-%d %H:%M UTC')}")
        self.stdout.write(f"{'=' * 60}\n")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️  Mode dry-run : aucune action ne sera exécutée\n")
            )

        # ── Étape 1 : Vérification des fichiers DTM ──────────────────────
        self.stdout.write("📁 Étape 1/4 — Vérification des fichiers DTM")
        missing = [f for f in [DTM_FILE, SLOPE_FILE, ASPECT_FILE] if not f.exists()]
        if missing:
            for f in missing:
                self.stdout.write(self.style.ERROR(f"   ❌ Fichier manquant : {f}"))
            self.stdout.write(
                self.style.ERROR(
                    "\n💡 Lancez d'abord create_dtm.py pour générer les fichiers DTM :\n"
                    "   python create_dtm.py \\\n"
                    "     --input media/lidar/votre_fichier.laz \\\n"
                    "     --output media/lidar/dtm_coste_belle.tif \\\n"
                    "     --calculate-slope --calculate-aspect"
                )
            )
            return
        self.stdout.write(self.style.SUCCESS("   ✅ DTM, slope, aspect trouvés\n"))

        # ── Étape 2 : Récupération Open-Meteo ────────────────────────────
        self.stdout.write("🌐 Étape 2/4 — Récupération Open-Meteo")

        station = self._get_station(station_id or LIDAR_STATION_ID)
        if station is None:
            return

        self.stdout.write(f"   🏔️  Station : {station.nom} (id={station.id})")
        self.stdout.write(
            f"   📍 Coordonnées : {station.geometry.y:.4f}, {station.geometry.x:.4f}"
        )

        snow_data = fetch_snow_for_station(station)

        if snow_data is None or snow_data.snow_depth_cm is None:
            self.stdout.write(
                self.style.WARNING("   ⚠️  Open-Meteo indisponible — fallback sur 75 cm")
            )
            base_snow_cm = 75.0
        else:
            base_snow_cm = snow_data.snow_depth_cm
            self.stdout.write(
                self.style.SUCCESS(f"   ❄️  Hauteur de neige réelle : {base_snow_cm} cm")
            )
        self.stdout.write("")

        # ── Étape 3 : Prédiction LIDAR ────────────────────────────────────
        self.stdout.write("🧮 Étape 3/4 — Prédiction d'accumulation de neige (LIDAR)")
        self.stdout.write(f"   Base snow : {base_snow_cm} cm")
        self.stdout.write(f"   Base elevation : {base_elevation} m")

        predict_cmd = [
            sys.executable,
            str(PREDICT_SCRIPT),
            "--dtm",
            str(DTM_FILE),
            "--slope",
            str(SLOPE_FILE),
            "--aspect",
            str(ASPECT_FILE),
            "--output",
            str(SNOW_PREDICTION_FILE),
            "--base-snow",
            str(base_snow_cm),
            "--base-elevation",
            str(base_elevation),
            "--save-classified",
            "--quiet",
        ]

        if not dry_run:
            success = self._run(predict_cmd)
            if not success:
                return
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✅ Prédiction sauvegardée → {SNOW_PREDICTION_FILE.name}\n"
                    f"   ✅ Classifiée sauvegardée → {SNOW_CLASSIFIED_FILE.name}"
                )
            )
        else:
            self.stdout.write(f"   [dry-run] {' '.join(predict_cmd)}")
        self.stdout.write("")

        # ── Étape 4a : Conversion en GeoJSON ─────────────────────────────
        self.stdout.write("🗺️  Étape 4/4 — Conversion en GeoJSON (Mapbox)")
        self.stdout.write(f"   Simplification : {simplify} m")

        convert_cmd = [
            sys.executable,
            str(CONVERT_SCRIPT),
            "--input",
            str(SNOW_CLASSIFIED_FILE),
            "--output",
            str(SNOW_GEOJSON_FILE),
            "--simplify",
            str(simplify),
            "--quiet",
        ]

        if not dry_run:
            success = self._run(convert_cmd)
            if not success:
                return
            geojson_size = SNOW_GEOJSON_FILE.stat().st_size / 1024
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✅ GeoJSON régénéré → {SNOW_GEOJSON_FILE.name} ({geojson_size:.1f} Ko)"
                )
            )
        else:
            self.stdout.write(f"   [dry-run] {' '.join(convert_cmd)}")
        self.stdout.write("")

        # ── Étape 4b : Sauvegarde en base ────────────────────────────────
        if not dry_run and snow_data is not None:
            SnowMeasure.objects.create(
                station=station,
                date_time=snow_data.fetched_at,
                temperature_c=snow_data.temperature_c,
                precipitation_mm=snow_data.precipitation_mm,
                total_snow_height_cm=snow_data.snow_depth_cm,
                natural_snow_height_cm=snow_data.snow_depth_cm,
                artificial_snow_height_cm=None,
                artificial_snow_production_m3=None,
            )
            self.stdout.write(
                self.style.SUCCESS("   ✅ Mesure sauvegardée en base (SnowMeasure)")
            )
            self.stdout.write("")

        # ── Résumé ────────────────────────────────────────────────────────
        self.stdout.write(f"{'=' * 60}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("✅ Dry-run terminé — aucune modification effectuée")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Carte de neige mise à jour avec {base_snow_cm} cm "
                    f"(source: {'Open-Meteo' if snow_data else 'fallback'})"
                )
            )
            self.stdout.write(
                "   → Rechargez la page et activez Neige: ON pour voir les nouvelles données"
            )
        self.stdout.write(f"{'=' * 60}\n")

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_station(self, station_id: int) -> Station | None:
        """Récupère la station cible par son ID."""
        try:
            return Station.objects.get(pk=station_id)
        except Station.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"   ❌ Station {station_id} introuvable\n"
                    f"   💡 Le LAZ disponible correspond à la station Ancelle (id={LIDAR_STATION_ID})"
                )
            )
            return None

    def _run(self, cmd: list[str]) -> bool:
        """
        Exécute une commande subprocess et affiche les erreurs si échec.

        Returns:
            True si succès, False sinon
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR),
            )
            if result.returncode != 0:
                self.stdout.write(
                    self.style.ERROR(
                        f"   ❌ Erreur (code {result.returncode}) :\n{result.stderr}"
                    )
                )
                return False
            return True
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"   ❌ Exception : {exc}"))
            return False
