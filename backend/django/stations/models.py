from django.contrib.gis.db import models

LIDAR_STATUS_CHOICES = [
    ("pending", "En attente"),
    ("running", "En cours"),
    ("done", "Terminé"),
    ("error", "Erreur"),
]

SNOW_STATUS_CHOICES = [
    ("none", "Aucun"),
    ("pending", "En attente"),
    ("running", "En cours"),
    ("done", "Terminé"),
    ("error", "Erreur"),
]


class Station(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    geometry = models.PointField(srid=4326, db_column="geom")

    class Meta:
        db_table = "stations"
        managed = True  # la table existe déjà (créée par init.sql)


class Piste(models.Model):
    id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, db_column="station_id", related_name="pistes"
    )
    nom = models.CharField(max_length=255)
    type = models.CharField(max_length=50, db_column="type", null=True, blank=True)
    etat = models.CharField(max_length=50, db_column="etat", null=True, blank=True)
    longueur = models.IntegerField(db_column="longueur", null=True, blank=True)
    geometry = models.LineStringField(srid=4326, db_column="geom")

    class Meta:
        db_table = "pistes"
        managed = True


class SnowMeasure(models.Model):
    id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        db_column="station_id",
        related_name="snow_measures",
    )
    date_time = models.DateTimeField(db_column="date_time")
    temperature_c = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    precipitation_mm = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    total_snow_height_cm = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    natural_snow_height_cm = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    artificial_snow_height_cm = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    artificial_snow_production_m3 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = "snow_measures"
        managed = True


class LidarUpload(models.Model):
    """
    Représente UN fichier LAZ uploadé pour une station.
    Plusieurs LAZ peuvent être uploadés pour la même station (zones différentes).
    Le pipeline DTM fusionne tous les LAZ d'une station en un seul DTM.
    """

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="lidar_uploads",
    )
    laz_file = models.FileField(upload_to="lidar/")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lidar_uploads"
        managed = True
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"LidarUpload({self.station.nom}, {self.original_filename})"


class LidarDTM(models.Model):
    """
    Représente l'état du DTM fusionné pour une station.
    Mis à jour chaque fois qu'un nouveau LAZ est uploadé et traité.
    Séparé de LidarSnow pour que le DTM et la neige aient des cycles indépendants.
    """

    station = models.OneToOneField(
        Station,
        on_delete=models.CASCADE,
        related_name="lidar_dtm",
    )
    status = models.CharField(
        max_length=20,
        choices=LIDAR_STATUS_CHOICES,
        default="pending",
    )
    progress_step = models.CharField(max_length=100, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    laz_count = models.IntegerField(default=0, help_text="Nombre de LAZ fusionnés")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lidar_dtm"
        managed = True

    def __str__(self):
        return f"LidarDTM({self.station.nom}, {self.status}, {self.laz_count} LAZ)"


class LidarSnow(models.Model):
    """
    Représente l'état du pipeline neige pour une station.
    Mis à jour quotidiennement par le cron (update_snow_map).
    Ne retraite pas le DTM, utilise celui existant.
    """

    station = models.OneToOneField(
        Station,
        on_delete=models.CASCADE,
        related_name="lidar_snow",
    )
    status = models.CharField(
        max_length=20,
        choices=SNOW_STATUS_CHOICES,
        default="none",
    )
    progress_step = models.CharField(max_length=100, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    base_snow_cm = models.FloatField(
        null=True,
        blank=True,
        help_text="Hauteur de neige de référence utilisée (depuis Open-Meteo)",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "lidar_snow"
        managed = True

    def __str__(self):
        return f"LidarSnow({self.station.nom}, {self.status}, {self.base_snow_cm} cm)"
