"""
Django management command pour explorer un fichier LIDAR
Usage: python manage.py explore_lidar --file media/lidar/fichier.laz
"""

from pathlib import Path

import numpy as np
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Explore et analyse un fichier LAZ/LAS"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Chemin vers le fichier LAZ/LAS à analyser",
        )

    def handle(self, *args, **options):
        filepath = options["file"]

        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
        self.stdout.write(self.style.SUCCESS(f"🔍 ANALYSE DU FICHIER LIDAR"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 60}\n"))

        # Vérifier que le fichier existe
        if not Path(filepath).exists():
            self.stdout.write(
                self.style.ERROR(f"❌ Le fichier {filepath} n'existe pas!")
            )
            return

        try:
            # Import ici pour éviter les erreurs si laspy n'est pas installé
            import laspy

            # Lire le fichier
            self.stdout.write(f"📂 Ouverture du fichier: {filepath}")
            las = laspy.read(filepath)
            self.stdout.write(self.style.SUCCESS(f"✅ Fichier chargé avec succès!\n"))

            # 1. INFORMATIONS GÉNÉRALES
            self.stdout.write(self.style.WARNING("📊 INFORMATIONS GÉNÉRALES"))
            self.stdout.write("-" * 60)
            self.stdout.write(f"Format: {las.header.version}")
            self.stdout.write(f"Nombre de points: {len(las.points):,}")
            file_size = Path(filepath).stat().st_size / (1024**2)
            self.stdout.write(f"Taille du fichier: {file_size:.2f} Mo")

            # 2. EMPRISE GÉOGRAPHIQUE
            self.stdout.write(self.style.WARNING("\n📍 EMPRISE GÉOGRAPHIQUE"))
            self.stdout.write("-" * 60)
            self.stdout.write(f"X min: {las.header.x_min:.2f}")
            self.stdout.write(f"X max: {las.header.x_max:.2f}")
            self.stdout.write(f"Y min: {las.header.y_min:.2f}")
            self.stdout.write(f"Y max: {las.header.y_max:.2f}")
            self.stdout.write(f"Z min (altitude): {las.header.z_min:.2f} m")
            self.stdout.write(f"Z max (altitude): {las.header.z_max:.2f} m")
            denivele = las.header.z_max - las.header.z_min
            self.stdout.write(self.style.SUCCESS(f"⛰️  Dénivelé: {denivele:.2f} m"))

            # 3. SYSTÈME DE COORDONNÉES
            self.stdout.write(self.style.WARNING("\n🌍 SYSTÈME DE COORDONNÉES"))
            self.stdout.write("-" * 60)
            try:
                crs = las.header.parse_crs()
                self.stdout.write(f"CRS: {crs}")
            except:
                self.stdout.write("CRS: Non spécifié (probablement Lambert 93 si IGN)")

            # 4. ATTRIBUTS DISPONIBLES
            self.stdout.write(self.style.WARNING("\n📋 ATTRIBUTS DISPONIBLES"))
            self.stdout.write("-" * 60)
            for dim in las.point_format.dimension_names:
                self.stdout.write(f"  - {dim}")

            # 5. CLASSIFICATION DES POINTS
            self.stdout.write(self.style.WARNING("\n🏷️  CLASSIFICATION DES POINTS"))
            self.stdout.write("-" * 60)

            if "classification" in las.point_format.dimension_names:
                unique_classes, counts = np.unique(
                    las.classification, return_counts=True
                )

                # Dictionnaire des classes LiDAR standard
                class_names = {
                    0: "Jamais classé",
                    1: "Non assigné",
                    2: "Sol",
                    3: "Végétation basse",
                    4: "Végétation moyenne",
                    5: "Végétation haute",
                    6: "Bâtiment",
                    9: "Eau",
                    17: "Pont",
                }

                for cls, count in zip(unique_classes, counts):
                    percentage = (count / len(las.points)) * 100
                    class_name = class_names.get(cls, f"Classe {cls}")

                    # Colorer en vert la classe "Sol" qui nous intéresse
                    if cls == 2:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  {cls:2d} - {class_name:25s}: {count:10,} points ({percentage:5.2f}%)"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"  {cls:2d} - {class_name:25s}: {count:10,} points ({percentage:5.2f}%)"
                        )
            else:
                self.stdout.write(
                    self.style.ERROR("  ❌ Pas de classification disponible")
                )

            # 6. STATISTIQUES D'ALTITUDE
            self.stdout.write(self.style.WARNING("\n⛰️  STATISTIQUES D'ALTITUDE"))
            self.stdout.write("-" * 60)
            z_values = las.z
            self.stdout.write(f"Altitude moyenne: {np.mean(z_values):.2f} m")
            self.stdout.write(f"Altitude médiane: {np.median(z_values):.2f} m")
            self.stdout.write(f"Écart-type: {np.std(z_values):.2f} m")

            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 60}"))
            self.stdout.write(self.style.SUCCESS("✅ Analyse terminée!"))
            self.stdout.write(self.style.SUCCESS(f"{'=' * 60}\n"))

        except ImportError:
            self.stdout.write(self.style.ERROR("❌ laspy n'est pas installé!"))
            self.stdout.write("Installez-le avec: pip install laspy")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erreur: {str(e)}"))
            import traceback

            self.stdout.write(traceback.format_exc())
