import json

from django.contrib.gis.geos import GEOSGeometry, LineString
from rest_framework import serializers

from .models import Piste, SnowMeasure, Station


class PisteSerializer(serializers.ModelSerializer):
    geometry = serializers.JSONField(required=False)
    station_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Piste
        fields = ("id", "nom", "type", "etat", "longueur", "geometry", "station_id")

    def to_representation(self, instance):
        """Convertir la géométrie PostGIS en GeoJSON pour la lecture"""
        ret = super().to_representation(instance)
        if instance.geometry:
            ret["geometry"] = json.loads(instance.geometry.geojson)
        else:
            ret["geometry"] = None
        return ret

    def create(self, validated_data):
        """Créer une piste avec géométrie GeoJSON"""
        geometry_data = validated_data.pop("geometry", None)
        station_id = validated_data.pop("station_id", None)

        if not station_id:
            raise serializers.ValidationError({"station_id": "Ce champ est requis"})

        try:
            station = Station.objects.get(id=station_id)
        except Station.DoesNotExist:
            raise serializers.ValidationError({"station_id": "Station introuvable"})

        if geometry_data:
            if (
                isinstance(geometry_data, dict)
                and geometry_data.get("type") == "LineString"
            ):
                coordinates = geometry_data.get("coordinates", [])
                if len(coordinates) < 2:
                    raise serializers.ValidationError(
                        {"geometry": "Au moins 2 points sont requis"}
                    )
                # Créer la LineString directement à partir des coordonnées
                line = LineString(coordinates, srid=4326)
                validated_data["geometry"] = line
            elif isinstance(geometry_data, str):
                # Si c'est une chaîne GeoJSON
                validated_data["geometry"] = GEOSGeometry(geometry_data, srid=4326)
            else:
                raise serializers.ValidationError(
                    {"geometry": "Format de géométrie invalide"}
                )

        validated_data["station"] = station
        return Piste.objects.create(**validated_data)


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
    station_nom = serializers.CharField(source="station.nom", read_only=True)
    station = StationSerializer(read_only=True)

    class Meta:
        model = SnowMeasure
        fields = (
            "id",
            "date_time",
            "temperature_c",
            "precipitation_mm",
            "total_snow_height_cm",
            "natural_snow_height_cm",
            "artificial_snow_height_cm",
            "artificial_snow_production_m3",
            "station_nom",
            "station",
        )
