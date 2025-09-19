from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Station, Piste, SnowMeasure
from .serializers import StationSerializer, PisteSerializer, SnowMeasureSerializer
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.utils.dateparse import parse_datetime

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
            queryset = queryset.annotate(distance=Distance('geometry', point)).filter(distance__lte=float(rayon))
        return queryset

    @action(detail=True, methods=['get', 'post'], url_path='snow_measures')
    def snow(self, request, pk=None):
        station = self.get_object()

        if request.method.lower() == 'get':
            start = request.query_params.get('start')
            end = request.query_params.get('end')
            limit = request.query_params.get('limit')

            mesures = SnowMeasure.objects.filter(station=station)
            if start:
                dt = parse_datetime(start)
                if dt:
                    mesures = mesures.filter(date_time__gte=dt)
            if end:
                dt = parse_datetime(end)
                if dt:
                    mesures = mesures.filter(date_time__lte=dt)
            mesures = mesures.order_by('-date_time')
            if limit:
                try:
                    mesures = mesures[: int(limit)]
                except Exception:
                    pass

            serializer = SnowMeasureSerializer(mesures, many=True)
            return Response(serializer.data)

        # POST
        serializer = SnowMeasureSerializer(data=request.data)
        if serializer.is_valid():
            mesure = SnowMeasure.objects.create(
                station=station,
                date_time=serializer.validated_data.get('date_time'),
                temperature_c=serializer.validated_data.get('temperature_c'),
                precipitation_mm=serializer.validated_data.get('precipitation_mm'),
                total_snow_height_cm=serializer.validated_data.get('total_snow_height_cm'),
                natural_snow_height_cm=serializer.validated_data.get('natural_snow_height_cm'),
                artificial_snow_height_cm=serializer.validated_data.get('artificial_snow_height_cm'),
                artificial_snow_production_m3=serializer.validated_data.get('artificial_snow_production_m3'),
            )
            return Response(SnowMeasureSerializer(mesure).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SnowMeasureViewSet(viewsets.ModelViewSet):
    queryset = SnowMeasure.objects.all()
    serializer_class = SnowMeasureSerializer
    
class PisteViewSet(viewsets.ModelViewSet):
    queryset = Piste.objects.all()
    serializer_class = PisteSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        station_id = self.request.query_params.get('station_id')
        if station_id:
            queryset = queryset.filter(station_id=station_id)
        return queryset
