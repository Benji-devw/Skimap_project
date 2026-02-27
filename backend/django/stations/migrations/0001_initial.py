import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        # Les tables stations, pistes, snow_measures existent déjà (créées par init.sql)
        # On les déclare sans les recréer grâce à SeparateDatabaseAndState
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Station",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        ("nom", models.CharField(max_length=255)),
                        (
                            "geometry",
                            django.contrib.gis.db.models.fields.PointField(
                                db_column="geom", srid=4326
                            ),
                        ),
                    ],
                    options={
                        "db_table": "stations",
                        "managed": True,
                    },
                ),
                migrations.CreateModel(
                    name="Piste",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        (
                            "station",
                            models.ForeignKey(
                                db_column="station_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="pistes",
                                to="stations.station",
                            ),
                        ),
                        ("nom", models.CharField(max_length=255)),
                        (
                            "type",
                            models.CharField(
                                blank=True,
                                db_column="type",
                                max_length=50,
                                null=True,
                            ),
                        ),
                        (
                            "etat",
                            models.CharField(
                                blank=True,
                                db_column="etat",
                                max_length=50,
                                null=True,
                            ),
                        ),
                        (
                            "longueur",
                            models.IntegerField(
                                blank=True, db_column="longueur", null=True
                            ),
                        ),
                        (
                            "geometry",
                            django.contrib.gis.db.models.fields.LineStringField(
                                db_column="geom", srid=4326
                            ),
                        ),
                    ],
                    options={
                        "db_table": "pistes",
                        "managed": True,
                    },
                ),
                migrations.CreateModel(
                    name="SnowMeasure",
                    fields=[
                        ("id", models.AutoField(primary_key=True, serialize=False)),
                        (
                            "station",
                            models.ForeignKey(
                                db_column="station_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="snow_measures",
                                to="stations.station",
                            ),
                        ),
                        ("date_time", models.DateTimeField(db_column="date_time")),
                        (
                            "temperature_c",
                            models.DecimalField(
                                blank=True,
                                decimal_places=2,
                                max_digits=5,
                                null=True,
                            ),
                        ),
                        (
                            "precipitation_mm",
                            models.DecimalField(
                                blank=True,
                                decimal_places=2,
                                max_digits=6,
                                null=True,
                            ),
                        ),
                        (
                            "total_snow_height_cm",
                            models.DecimalField(
                                blank=True,
                                decimal_places=2,
                                max_digits=6,
                                null=True,
                            ),
                        ),
                        (
                            "natural_snow_height_cm",
                            models.DecimalField(
                                blank=True,
                                decimal_places=2,
                                max_digits=6,
                                null=True,
                            ),
                        ),
                        (
                            "artificial_snow_height_cm",
                            models.DecimalField(
                                blank=True,
                                decimal_places=2,
                                max_digits=6,
                                null=True,
                            ),
                        ),
                        (
                            "artificial_snow_production_m3",
                            models.DecimalField(
                                blank=True,
                                decimal_places=2,
                                max_digits=10,
                                null=True,
                            ),
                        ),
                    ],
                    options={
                        "db_table": "snow_measures",
                        "managed": True,
                    },
                ),
            ],
            # Aucune opération SQL réelle pour ces 3 tables (elles existent déjà)
            database_operations=[],
        ),
        # lidar_uploads n'existe pas encore → on la crée vraiment
        migrations.CreateModel(
            name="LidarUpload",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "station",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lidar_upload",
                        to="stations.station",
                    ),
                ),
                ("laz_file", models.FileField(upload_to="lidar/")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "En attente"),
                            ("running", "En cours"),
                            ("done", "Terminé"),
                            ("error", "Erreur"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "progress_step",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(null=True, blank=True)),
            ],
            options={
                "db_table": "lidar_uploads",
                "managed": True,
            },
        ),
    ]
