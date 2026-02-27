import json
from pathlib import Path

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import LidarUpload, Piste, SnowMeasure, Station
from .serializers import PisteSerializer, SnowMeasureSerializer, StationSerializer
from .services.lidar_pipeline import (
    cancel_pipeline,
    delete_laz_upload,
    dtm_ready,
    run_dtm_pipeline_async,
    run_snow_pipeline_async,
    snow_geojson_path,
)
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
    Endpoint pour servir les données de couverture neigeuse au format GeoJSON.

    GET /api/snow-coverage/?station_id=3

    Query params:
        station_id (optionnel) : ID de la station. Si absent, retourne le fichier
                                 générique (snow_contours.geojson) pour compatibilité.

    Returns:
        GeoJSON FeatureCollection avec polygones colorés par hauteur de neige
    """
    from .services.lidar_pipeline import snow_geojson_path

    station_id = request.GET.get("station_id")

    if station_id:
        # GeoJSON spécifique à la station (généré par le pipeline upload)
        try:
            station_id_int = int(station_id)
        except ValueError:
            return JsonResponse(
                {
                    "error": "Invalid parameter",
                    "message": "station_id doit être un entier",
                },
                status=400,
            )
        geojson_path = snow_geojson_path(station_id_int)
    else:
        # Fallback : fichier générique (rétrocompatibilité)
        geojson_path = (
            Path(__file__).parent.parent / "media" / "lidar" / "snow_contours.geojson"
        )

    if not geojson_path.exists():
        return JsonResponse(
            {
                "error": "Snow coverage data not available",
                "message": "GeoJSON non disponible. Uploadez un fichier LAZ pour cette station.",
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


@api_view(["POST"])
def lidar_upload(request):
    """
    Upload d'un fichier LAZ et lancement du pipeline de traitement en arrière-plan.

    POST /api/lidar/upload/
    Content-Type: multipart/form-data

    Body:
        station_id : int  — ID de la station associée
        laz_file   : file — Fichier .laz ou .copc.laz

    Returns:
        { "upload_id": 42, "status": "pending", "message": "..." }
    """
    parser_classes = [MultiPartParser]

    station_id = request.data.get("station_id")
    laz_file = request.FILES.get("laz_file")

    # Validations
    if not station_id:
        return JsonResponse(
            {"error": "Missing parameter", "message": "station_id est requis"},
            status=400,
        )
    if not laz_file:
        return JsonResponse(
            {"error": "Missing file", "message": "laz_file est requis"},
            status=400,
        )

    ext = Path(laz_file.name).suffix.lower()
    if ext not in (".laz", ".las"):
        return JsonResponse(
            {
                "error": "Invalid file",
                "message": f"Format non supporté : {ext}. Utilisez .laz ou .las",
            },
            status=400,
        )

    try:
        station = Station.objects.get(pk=int(station_id))
    except (Station.DoesNotExist, ValueError):
        return JsonResponse(
            {
                "error": "Station not found",
                "message": f"Station {station_id} introuvable",
            },
            status=404,
        )

    # Sauvegarder le nouveau LAZ (sans écraser les précédents)
    upload = LidarUpload.objects.create(
        station=station,
        laz_file=laz_file,
        original_filename=laz_file.name,
    )

    # Compter le total de LAZ pour cette station
    laz_count = LidarUpload.objects.filter(station=station).count()

    # Lancer le pipeline DTM (qui fusionnera tous les LAZ puis lancera le pipeline neige)
    # Si un pipeline tourne déjà, on refuse l'upload pour éviter les conflits
    from .services.lidar_pipeline import dtm_pipeline_is_running

    if dtm_pipeline_is_running(station.id):
        # Supprimer le fichier qu'on vient de sauvegarder
        upload.laz_file.delete(save=False)
        upload.delete()
        return JsonResponse(
            {
                "error": "Pipeline already running",
                "message": (
                    "Un traitement DTM est déjà en cours pour cette station. "
                    "Attendez qu'il se termine ou annulez-le avant d'uploader un nouveau fichier."
                ),
            },
            status=409,
        )

    run_dtm_pipeline_async(station.id)

    return JsonResponse(
        {
            "upload_id": upload.id,
            "station_id": station.id,
            "station_nom": station.nom,
            "laz_count": laz_count,
            "message": (
                f"Fichier reçu pour {station.nom} "
                f"({laz_count} LAZ au total). "
                f"Pipeline DTM démarré en arrière-plan."
            ),
        },
        status=202,
    )


@api_view(["GET"])
def lidar_status(request):
    """
    Retourne l'état du pipeline LIDAR pour une station.

    GET /api/lidar/status/?station_id=3

    Returns:
        {
            "station_id": 3,
            "station_nom": "Ancelle",
            "status": "running",          // pending | running | done | error
            "progress_step": "Génération DTM…",
            "error_message": "",
            "uploaded_at": "2024-01-15T14:00:00Z",
            "processed_at": null,
            "snow_layer_ready": false      // true quand le GeoJSON est disponible
        }
    """
    station_id = request.GET.get("station_id")

    if not station_id:
        return JsonResponse(
            {"error": "Missing parameter", "message": "station_id est requis"},
            status=400,
        )

    try:
        station = Station.objects.get(pk=int(station_id))
    except (Station.DoesNotExist, ValueError):
        return JsonResponse(
            {
                "error": "Station not found",
                "message": f"Station {station_id} introuvable",
            },
            status=404,
        )

    from .models import LidarDTM, LidarSnow

    # Récupérer les statuts DTM et neige séparément
    try:
        dtm_record = LidarDTM.objects.get(station=station)
        dtm_status = dtm_record.status
        dtm_step = dtm_record.progress_step
        dtm_error = dtm_record.error_message
        dtm_laz_count = dtm_record.laz_count
        dtm_completed_at = (
            dtm_record.completed_at.isoformat() if dtm_record.completed_at else None
        )
    except LidarDTM.DoesNotExist:
        dtm_status = "none"
        dtm_step = ""
        dtm_error = ""
        dtm_laz_count = 0
        dtm_completed_at = None

    try:
        snow_record = LidarSnow.objects.get(station=station)
        snow_status = snow_record.status
        snow_step = snow_record.progress_step
        snow_error = snow_record.error_message
        snow_base_cm = snow_record.base_snow_cm
        snow_completed_at = (
            snow_record.completed_at.isoformat() if snow_record.completed_at else None
        )
    except LidarSnow.DoesNotExist:
        snow_status = "none"
        snow_step = ""
        snow_error = ""
        snow_base_cm = None
        snow_completed_at = None

    laz_count = LidarUpload.objects.filter(station=station).count()
    geojson_ready = snow_geojson_path(station.id).exists()

    # Le statut global est le plus avancé des deux pipelines
    # Si le DTM tourne, c'est le statut principal affiché
    if dtm_status in ("pending", "running"):
        global_status = dtm_status
        global_step = dtm_step
    elif snow_status in ("pending", "running"):
        global_status = snow_status
        global_step = snow_step
    elif snow_status == "done" and geojson_ready:
        global_status = "done"
        global_step = snow_step
    elif dtm_status == "error":
        global_status = "error"
        global_step = dtm_error
    elif snow_status == "error":
        global_status = "error"
        global_step = snow_error
    else:
        global_status = "none"
        global_step = ""

    return JsonResponse(
        {
            "station_id": station.id,
            "station_nom": station.nom,
            "laz_count": laz_count,
            # Statut global (pour le frontend)
            "status": global_status,
            "progress_step": global_step,
            # Détail DTM
            "dtm": {
                "status": dtm_status,
                "progress_step": dtm_step,
                "error_message": dtm_error,
                "laz_count": dtm_laz_count,
                "completed_at": dtm_completed_at,
                "ready": dtm_ready(station.id),
            },
            # Détail neige
            "snow": {
                "status": snow_status,
                "progress_step": snow_step,
                "error_message": snow_error,
                "base_snow_cm": snow_base_cm,
                "completed_at": snow_completed_at,
            },
            "snow_layer_ready": geojson_ready,
        }
    )


@api_view(["POST"])
def lidar_cancel(request):
    """
    Annule le pipeline DTM ou neige en cours pour une station.

    POST /api/lidar/cancel/
    Body: { "station_id": 3 }

    Returns:
        { "station_id": 3, "cancelled": true, "message": "..." }
    """
    station_id = request.data.get("station_id")

    if not station_id:
        return JsonResponse(
            {"error": "Missing parameter", "message": "station_id est requis"},
            status=400,
        )

    try:
        station = Station.objects.get(pk=int(station_id))
    except (Station.DoesNotExist, ValueError):
        return JsonResponse(
            {
                "error": "Station not found",
                "message": f"Station {station_id} introuvable",
            },
            status=404,
        )

    was_running = cancel_pipeline(station.id)

    return JsonResponse(
        {
            "station_id": station.id,
            "station_nom": station.nom,
            "cancelled": was_running,
            "message": (
                f"Pipeline annulé pour {station.nom}."
                if was_running
                else f"Aucun pipeline en cours pour {station.nom}."
            ),
        }
    )


@api_view(["POST"])
def snow_refresh(request):
    """
    Déclenche manuellement le pipeline neige pour une station.
    Utilise le DTM existant — ne retraite pas les LAZ.

    POST /api/snow/refresh/
    Body: { "station_id": 3 }
    """
    station_id = request.data.get("station_id")

    if not station_id:
        return JsonResponse(
            {"error": "Missing parameter", "message": "station_id est requis"},
            status=400,
        )

    try:
        station = Station.objects.get(pk=int(station_id))
    except (Station.DoesNotExist, ValueError):
        return JsonResponse(
            {
                "error": "Station not found",
                "message": f"Station {station_id} introuvable",
            },
            status=404,
        )

    if not dtm_ready(station.id):
        return JsonResponse(
            {
                "error": "DTM not available",
                "message": "Uploadez d'abord un fichier LAZ pour générer le DTM.",
            },
            status=409,
        )

    run_snow_pipeline_async(station.id)

    return JsonResponse(
        {
            "station_id": station.id,
            "station_nom": station.nom,
            "message": f"Pipeline neige démarré pour {station.nom}.",
        },
        status=202,
    )


@api_view(["GET"])
def lidar_uploads_list(request):
    """
    Liste tous les fichiers LAZ uploadés pour une station.

    GET /api/lidar/uploads/?station_id=3

    Returns:
        {
            "station_id": 3,
            "station_nom": "Ancelle",
            "uploads": [
                {
                    "id": 12,
                    "original_filename": "zone_nord.laz",
                    "uploaded_at": "2024-01-15T14:00:00Z",
                    "file_size_mb": 45.2,
                    "file_exists": true
                },
                ...
            ]
        }
    """
    station_id = request.GET.get("station_id")

    if not station_id:
        return JsonResponse(
            {"error": "Missing parameter", "message": "station_id est requis"},
            status=400,
        )

    try:
        station = Station.objects.get(pk=int(station_id))
    except (Station.DoesNotExist, ValueError):
        return JsonResponse(
            {
                "error": "Station not found",
                "message": f"Station {station_id} introuvable",
            },
            status=404,
        )

    from .models import LidarUpload
    from .services.lidar_pipeline import BASE_DIR

    uploads = LidarUpload.objects.filter(station=station).order_by("uploaded_at")

    uploads_data = []
    for u in uploads:
        disk_path = BASE_DIR / u.laz_file.name
        try:
            size_mb = (
                round(disk_path.stat().st_size / (1024 * 1024), 2)
                if disk_path.exists()
                else None
            )
        except Exception:
            size_mb = None

        uploads_data.append(
            {
                "id": u.id,
                "original_filename": u.original_filename or u.laz_file.name,
                "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
                "file_size_mb": size_mb,
                "file_exists": disk_path.exists(),
            }
        )

    return JsonResponse(
        {
            "station_id": station.id,
            "station_nom": station.nom,
            "uploads": uploads_data,
        }
    )


@api_view(["DELETE"])
def lidar_upload_delete(request, upload_id: int):
    """
    Supprime un fichier LAZ uploadé et invalide les fichiers générés pour la station.
    Si d'autres LAZ restent, re-déclenche automatiquement le pipeline DTM.
    Si c'était le dernier LAZ, supprime aussi LidarDTM et LidarSnow.

    DELETE /api/lidar/uploads/<upload_id>/

    Returns:
        {
            "upload_id": 12,
            "station_id": 3,
            "file_deleted": true,
            "remaining_laz": 1,
            "pipeline_restarted": true,
            "message": "..."
        }
    """
    try:
        result = delete_laz_upload(upload_id)
    except ValueError as e:
        return JsonResponse(
            {"error": "Not found", "message": str(e)},
            status=404,
        )
    except Exception as e:
        return JsonResponse(
            {"error": "Delete failed", "message": str(e)},
            status=500,
        )

    remaining = result["remaining_laz"]
    restarted = result["pipeline_restarted"]

    if remaining == 0:
        message = (
            "Fichier LAZ supprimé. Aucun LAZ restant — données LIDAR réinitialisées."
        )
    elif restarted:
        message = (
            f"Fichier LAZ supprimé. "
            f"{remaining} fichier(s) restant(s) — pipeline DTM redémarré."
        )
    else:
        message = "Fichier LAZ supprimé."

    return JsonResponse(
        {
            **result,
            "message": message,
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
