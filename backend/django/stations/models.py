from django.contrib.gis.db import models

class Station(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    geometry = models.PointField(srid=4326, db_column='geom')

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
    type = models.CharField(max_length=50, db_column='type', null=True, blank=True)
    etat = models.CharField(max_length=50, db_column='etat', null=True, blank=True)
    longueur = models.IntegerField(db_column='longueur', null=True, blank=True)
    geometry = models.LineStringField(srid=4326, db_column='geom')

    class Meta:
        db_table = 'pistes'
        managed = False