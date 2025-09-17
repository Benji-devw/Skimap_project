from rest_framework import serializers
from .models import Station, Piste, SnowMeasure
import json

class PisteSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    def get_geometry(self, obj: Piste):
        if not obj.geometry:
            return None
        return json.loads(obj.geometry.geojson)

    class Meta:
        model = Piste
        fields = ("id", "nom", "type", "etat", "longueur", "geometry")

class StationSerializer(serializers.ModelSerializer):
    pistes = PisteSerializer(many=True, read_only=True)
    geometry = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()

    def get_geometry(self, obj: Station):
        if not obj.geometry:
            return None
        return json.loads(obj.geometry.geojson)

    def get_longitude(self, obj: Station):
        return float(obj.geometry.x) if obj.geometry else None

    def get_latitude(self, obj: Station):
        return float(obj.geometry.y) if obj.geometry else None

    class Meta:
        model = Station
        fields = ("id", "nom", "longitude", "latitude", "geometry", "pistes")


class SnowMeasureSerializer(serializers.ModelSerializer):
    station_nom = serializers.CharField(source='station.nom', read_only=True)
    station_id = serializers.IntegerField(source='station_id', read_only=True)
    station = StationSerializer(read_only=True)
    class Meta:
        model = SnowMeasure
        fields = (
            "id",
            "date_heure",
            "temperature_c",
            "precipitations_mm",
            "hauteur_neige_totale_cm",
            "hauteur_neige_naturelle_cm",
            "hauteur_neige_artificielle_cm",
            "production_neige_artificielle_m3",
            "station_id",
            "station_nom",
            "station",  
        )