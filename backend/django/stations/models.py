from django.contrib.gis.db import models

class Station(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = 'stations'
        managed = False  # la table existe déjà (créée par init.sql)

class Piste(models.Model):
    id = models.AutoField(primary_key=True)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE,
        db_column='station_id', related_name='pistes'
    )
    nom = models.CharField(max_length=255)
    geom = models.LineStringField(srid=4326)

    class Meta:
        db_table = 'pistes'
        managed = False