from rest_framework import serializers
from .models import Station, Piste

class PisteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Piste
        fields = ("id", "nom", "geom")

class StationSerializer(serializers.ModelSerializer):
    pistes = PisteSerializer(many=True, read_only=True)

    class Meta:
        model = Station
        fields = ("id", "nom", "geom", "pistes")