from typing import Any, Dict, List
from django.db import connection
from django.http import JsonResponse, HttpRequest
import json

def stations(request: HttpRequest) -> JsonResponse:
    with connection.cursor() as cur:
        cur.execute("""
            SELECT id, nom, ST_X(geom) AS longitude, ST_Y(geom) AS latitude
            FROM stations ORDER BY id
        """)
        rows = cur.fetchall()
    data: List[Dict[str, Any]] = [
        {"id": r[0], "nom": r[1], "longitude": float(r[2]), "latitude": float(r[3])}
        for r in rows
    ]
    return JsonResponse(data, safe=False)

def pistes_par_station(request: HttpRequest, station_id: int) -> JsonResponse:
    with connection.cursor() as cur:
        cur.execute("""
            SELECT id, nom, ST_AsGeoJSON(geom) AS geojson
            FROM pistes WHERE station_id = %s ORDER BY id
        """, [station_id])
        rows = cur.fetchall()
    data: List[Dict[str, Any]] = [
        {"id": r[0], "nom": r[1], "geometry": json.loads(r[2]) if r[2] else None}
        for r in rows
    ]
    return JsonResponse(data, safe=False)

def stations_proches(request: HttpRequest) -> JsonResponse:
    try:
        lat = float(request.GET.get("lat"))
        lng = float(request.GET.get("lng"))
        rayon = int(request.GET.get("rayon", "50000"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Paramètres lat,lng (float) requis; rayon (int) optionnel"}, status=400)

    with connection.cursor() as cur:
        cur.execute("""
            SELECT id, nom, ST_X(geom) AS longitude, ST_Y(geom) AS latitude
            FROM stations
            WHERE ST_DWithin(
              geom::geography,
              ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
              %s
            )
            ORDER BY id
        """, [lng, lat, rayon])
        rows = cur.fetchall()
    data: List[Dict[str, Any]] = [
        {"id": r[0], "nom": r[1], "longitude": float(r[2]), "latitude": float(r[3])}
        for r in rows
    ]
    return JsonResponse(data, safe=False)