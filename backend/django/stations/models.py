from django.contrib.gis.db import models

class Station(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    geometry = models.PointField(srid=4326, db_column='geom')

    class Meta:
        db_table = 'stations'
        managed = True  # la table existe déjà (créée par init.sql)

class Piste(models.Model):
    id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE,
        db_column='station_id', related_name='pistes'
    )
    nom = models.CharField(max_length=255)
    type = models.CharField(max_length=50, db_column='type', null=True, blank=True)
    etat = models.CharField(max_length=50, db_column='etat', null=True, blank=True)
    longueur = models.IntegerField(db_column='longueur', null=True, blank=True)
    geometry = models.LineStringField(srid=4326, db_column='geom')

    class Meta:
        db_table = 'pistes'
        managed = True


class SnowMeasure(models.Model):
    id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        db_column='station_id',
        related_name='snow_measures',
    )
    date_heure = models.DateTimeField(db_column='date_heure')
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    precipitations_mm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    hauteur_neige_totale_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    hauteur_neige_naturelle_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    hauteur_neige_artificielle_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    production_neige_artificielle_m3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'snow_measures'
        managed = True