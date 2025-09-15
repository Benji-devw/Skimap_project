from rest_framework import viewsets
from .models import Station, Piste
from .serializers import StationSerializer, PisteSerializer
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance

# Create your views here.

class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer

    # Recherche spatiale
    def get_queryset(self):
        queryset = super().get_queryset()
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        rayon = self.request.query_params.get('rayon')  # en mètres
        if lat and lng and rayon:
            point = Point(float(lng), float(lat), srid=4326)
            queryset = queryset.annotate(distance=Distance('geom', point)).filter(distance__lte=float(rayon))
        return queryset

class PisteViewSet(viewsets.ModelViewSet):
    queryset = Piste.objects.all()
    serializer_class = PisteSerializer
