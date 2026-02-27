"""
Commande Django pour récupérer les données de neige depuis Open-Meteo
et les sauvegarder en base de données (modèle SnowMeasure).

Usage :
    python manage.py fetch_snow_data
    python manage.py fetch_snow_data --station-id 1
    python manage.py fetch_snow_data --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from stations.models import SnowMeasure, Station
from stations.services.open_meteo import (
    fetch_snow_for_all_stations,
    fetch_snow_for_station,
)


class Command(BaseCommand):
    help = "Récupère les données de neige depuis Open-Meteo et les sauvegarde en base"

    def add_arguments(self, parser):
        parser.add_argument(
            "--station-id",
            type=int,
            default=None,
            help="ID d'une station spécifique (par défaut : toutes les stations)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les données sans les sauvegarder en base",
        )

    def handle(self, *args, **options):
        station_id = options["station_id"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  Mode dry-run : aucune donnée ne sera sauvegardée\n"
                )
            )

        # ── Récupération des données ─────────────────────────────────────
        if station_id:
            try:
                station = Station.objects.get(pk=station_id)
            except Station.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"❌ Station {station_id} introuvable")
                )
                return

            self.stdout.write(
                f"🔍 Récupération pour la station : {station.nom} (id={station.id})"
            )
            snow_data_list = []
            data = fetch_snow_for_station(station)
            if data:
                snow_data_list.append(data)
        else:
            self.stdout.write("🔍 Récupération pour toutes les stations...")
            snow_data_list = fetch_snow_for_all_stations()

        if not snow_data_list:
            self.stdout.write(
                self.style.ERROR("❌ Aucune donnée récupérée depuis Open-Meteo")
            )
            return

        # ── Affichage et sauvegarde ──────────────────────────────────────
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(
            f"❄️  DONNÉES OPEN-METEO — {timezone.now().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        self.stdout.write(f"{'=' * 60}\n")

        saved_count = 0

        for data in snow_data_list:
            try:
                station = Station.objects.get(pk=data.station_id)
            except Station.DoesNotExist:
                continue

            # Affichage
            self.stdout.write(f"🏔️  {station.nom} (id={station.id})")
            self.stdout.write(
                f"   📍 Coordonnées   : {data.latitude:.4f}, {data.longitude:.4f}"
            )
            self.stdout.write(
                f"   ❄️  Hauteur neige  : "
                + (
                    self.style.SUCCESS(f"{data.snow_depth_cm} cm")
                    if data.snow_depth_cm
                    else "N/A"
                )
            )
            self.stdout.write(
                f"   🌨️  Chute de neige : "
                + (f"{data.snowfall_cm} cm" if data.snowfall_cm is not None else "N/A")
            )
            self.stdout.write(
                f"   🌡️  Température    : "
                + (
                    f"{data.temperature_c} °C"
                    if data.temperature_c is not None
                    else "N/A"
                )
            )
            self.stdout.write(
                f"   💧 Précipitations : "
                + (
                    f"{data.precipitation_mm} mm"
                    if data.precipitation_mm is not None
                    else "N/A"
                )
            )
            self.stdout.write("")

            if dry_run:
                continue

            # Sauvegarde en base
            SnowMeasure.objects.create(
                station=station,
                date_time=data.fetched_at,
                temperature_c=data.temperature_c,
                precipitation_mm=data.precipitation_mm,
                total_snow_height_cm=data.snow_depth_cm,
                natural_snow_height_cm=data.snow_depth_cm,  # Open-Meteo ne distingue pas naturel/artificiel
                artificial_snow_height_cm=None,
                artificial_snow_production_m3=None,
            )
            saved_count += 1

        # ── Résumé ───────────────────────────────────────────────────────
        self.stdout.write(f"{'=' * 60}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"✅ Dry-run terminé — {len(snow_data_list)} stations analysées, rien sauvegardé"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {saved_count}/{len(snow_data_list)} mesures sauvegardées en base"
                )
            )
        self.stdout.write(f"{'=' * 60}\n")
