import json
from pathlib import Path

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Piste, SnowMeasure, Station
from .serializers import PisteSerializer, SnowMeasureSerializer, StationSerializer
from .services.open_meteo import fetch_snow_for_station

# Create your views here.


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer

    # Recherche spatiale
    def get_queryset(self):
        queryset = super().get_queryset()
        lat = self.request.query_params.get("lat")
        lng = self.request.query_params.get("lng")
        rayon = self.request.query_params.get("rayon")  # en mètres
        if lat and lng and rayon:
            point = Point(float(lng), float(lat), srid=4326)
            queryset = queryset.annotate(distance=Distance("geometry", point)).filter(
                distance__lte=float(rayon)
            )
        return queryset

    @action(detail=True, methods=["get", "post"], url_path="snow_measures")
    def snow(self, request, pk=None):
        station = self.get_object()

        if request.method.lower() == "get":
            start = request.query_params.get("start")
            end = request.query_params.get("end")
            limit = request.query_params.get("limit")

            mesures = SnowMeasure.objects.filter(station=station)
            if start:
                dt = parse_datetime(start)
                if dt:
                    mesures = mesures.filter(date_time__gte=dt)
            if end:
                dt = parse_datetime(end)
                if dt:
                    mesures = mesures.filter(date_time__lte=dt)
            mesures = mesures.order_by("-date_time")
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
                date_time=serializer.validated_data.get("date_time"),
                temperature_c=serializer.validated_data.get("temperature_c"),
                precipitation_mm=serializer.validated_data.get("precipitation_mm"),
                total_snow_height_cm=serializer.validated_data.get(
                    "total_snow_height_cm"
                ),
                natural_snow_height_cm=serializer.validated_data.get(
                    "natural_snow_height_cm"
                ),
                artificial_snow_height_cm=serializer.validated_data.get(
                    "artificial_snow_height_cm"
                ),
                artificial_snow_production_m3=serializer.validated_data.get(
                    "artificial_snow_production_m3"
                ),
            )
            return Response(
                SnowMeasureSerializer(mesure).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SnowMeasureViewSet(viewsets.ModelViewSet):
    queryset = SnowMeasure.objects.all()
    serializer_class = SnowMeasureSerializer


class PisteViewSet(viewsets.ModelViewSet):
    queryset = Piste.objects.all()
    serializer_class = PisteSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        station_id = self.request.query_params.get("station_id")
        if station_id:
            queryset = queryset.filter(station_id=station_id)
        return queryset


@api_view(["GET"])
def snow_coverage_geojson(request):
    """
    Endpoint pour servir les données de couverture neigeuse au format GeoJSON
    Basé sur l'analyse LIDAR et le modèle d'accumulation

    GET /api/snow-coverage/

    Returns:
        GeoJSON FeatureCollection avec polygones colorés par hauteur de neige
    """
    # Chemin vers le fichier GeoJSON généré
    geojson_path = (
        Path(__file__).parent.parent / "media" / "lidar" / "snow_contours.geojson"
    )

    if not geojson_path.exists():
        return JsonResponse(
            {
                "error": "Snow coverage data not available",
                "message": "GeoJSON file not found. Run the LIDAR processing pipeline first.",
            },
            status=404,
        )

    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        return JsonResponse(geojson_data, safe=False)

    except Exception as e:
        return JsonResponse(
            {"error": "Failed to load snow coverage data", "message": str(e)},
            status=500,
        )


@api_view(["GET"])
def snow_realtime(request):
    """
    Retourne les données de neige en temps réel depuis Open-Meteo pour une station.

    GET /api/snow-realtime/?station_id=1

    Query params:
        station_id: ID de la station

    Returns:
        {
            "station_id": 1,
            "station_nom": "Coste Belle",
            "fetched_at": "2024-01-15T14:00:00Z",
            "snow_depth_cm": 68.0,
            "snowfall_cm": 2.5,
            "temperature_c": -3.1,
            "precipitation_mm": 1.2,
            "source": "open-meteo"
        }
    """
    station_id = request.GET.get("station_id")

    if not station_id:
        return JsonResponse(
            {"error": "Missing parameter", "message": "station_id is required"},
            status=400,
        )

    try:
        station = Station.objects.get(pk=int(station_id))
    except (Station.DoesNotExist, ValueError):
        return JsonResponse(
            {
                "error": "Station not found",
                "message": f"No station with id={station_id}",
            },
            status=404,
        )

    data = fetch_snow_for_station(station)

    if data is None:
        return JsonResponse(
            {
                "error": "Open-Meteo unavailable",
                "message": "Could not fetch snow data from Open-Meteo",
            },
            status=503,
        )

    return JsonResponse(
        {
            "station_id": station.id,
            "station_nom": station.nom,
            "latitude": data.latitude,
            "longitude": data.longitude,
            "fetched_at": data.fetched_at.isoformat(),
            "snow_depth_cm": data.snow_depth_cm,
            "snowfall_cm": data.snowfall_cm,
            "temperature_c": data.temperature_c,
            "precipitation_mm": data.precipitation_mm,
            "source": "open-meteo",
        }
    )


@api_view(["GET"])
def snow_at_point(request):
    """
    Retourne la hauteur de neige prédite pour une coordonnée donnée

    GET /api/snow-at-point/?lat=44.602&lng=6.220

    Query params:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)

    Returns:
        {
            "snow_height_cm": 68.5,
            "category": "moyen",
            "color": "#66FF66",
            "range": "50-80 cm"
        }
    """
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")

    if not lat or not lng:
        return JsonResponse(
            {"error": "Missing parameters", "message": "lat and lng are required"},
            status=400,
        )

    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return JsonResponse(
            {"error": "Invalid parameters", "message": "lat and lng must be numbers"},
            status=400,
        )

    # Charger le GeoJSON
    geojson_path = (
        Path(__file__).parent.parent / "media" / "lidar" / "snow_contours.geojson"
    )

    if not geojson_path.exists():
        return JsonResponse({"error": "Snow coverage data not available"}, status=404)

    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        # Vérifier dans quel polygone se trouve le point
        from shapely.geometry import Point as ShapelyPoint
        from shapely.geometry import shape

        point = ShapelyPoint(lng, lat)

        for feature in geojson_data["features"]:
            polygon = shape(feature["geometry"])
            if polygon.contains(point):
                # Point trouvé dans ce polygone
                props = feature["properties"]
                return JsonResponse(
                    {
                        "snow_height_cm": props.get("class", 0) * 20
                        + 10,  # Estimation moyenne
                        "category": props.get("name", "Unknown"),
                        "color": props.get("color", "#FFFFFF"),
                        "range": props.get("snow_range", "N/A"),
                        "description": props.get("description", ""),
                    }
                )

        # Point hors de la zone couverte
        return JsonResponse(
            {
                "snow_height_cm": None,
                "category": "out_of_bounds",
                "message": "Point outside coverage area",
            }
        )

    except Exception as e:
        return JsonResponse(
            {"error": "Failed to process request", "message": str(e)}, status=500
        )
