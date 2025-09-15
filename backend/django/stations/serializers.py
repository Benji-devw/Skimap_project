from rest_framework import serializers
from .models import Station, Piste
import json

class PisteSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    def get_geometry(self, obj: Piste):
        if not obj.geometry:
            return None
        return json.loads(obj.geometry.geojson)

    class Meta:
        model = Piste
        fields = ("id", "nom", "geometry")

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