"""
Service pour récupérer les données de neige en temps réel depuis Open-Meteo
Documentation API : https://open-meteo.com/en/docs

Open-Meteo est gratuit, sans clé API requise.

Variables récupérées :
    - snow_depth           : Profondeur de neige au sol (cm)
    - snowfall             : Chute de neige des dernières heures (cm)
    - temperature_2m       : Température à 2m (°C)
    - precipitation        : Précipitations (mm)
"""

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# URL de base de l'API Open-Meteo
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Variables météo à récupérer
HOURLY_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "snowfall",
    "snow_depth",
]


@dataclass
class SnowData:
    """Données de neige récupérées depuis Open-Meteo pour une station"""

    station_id: int
    latitude: float
    longitude: float
    fetched_at: datetime

    # Données actuelles
    snow_depth_cm: Optional[float]  # Hauteur de neige au sol (cm)
    snowfall_cm: Optional[float]  # Chute de neige récente (cm)
    temperature_c: Optional[float]  # Température actuelle (°C)
    precipitation_mm: Optional[float]  # Précipitations (mm)

    def __str__(self):
        return (
            f"Station {self.station_id} @ ({self.latitude:.4f}, {self.longitude:.4f}) — "
            f"Neige: {self.snow_depth_cm} cm, "
            f"Temp: {self.temperature_c}°C, "
            f"Précip: {self.precipitation_mm} mm"
        )


def fetch_snow_for_station(station) -> Optional[SnowData]:
    """
    Récupère les données de neige actuelles depuis Open-Meteo pour une station.

    Open-Meteo retourne des séries horaires. On prend le dernier index
    disponible (heure la plus récente non-nulle).

    Args:
        station: Instance du modèle Station (doit avoir .geometry et .id)

    Returns:
        SnowData ou None en cas d'erreur
    """
    lat = station.geometry.y
    lng = station.geometry.x

    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "UTC",
        "forecast_days": 1,
    }

    url = f"{OPEN_METEO_BASE_URL}?{urllib.parse.urlencode(params)}"

    logger.info(
        f"[OpenMeteo] Requête pour station {station.id} ({station.nom}) → {url}"
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
    except Exception as exc:
        logger.error(f"[OpenMeteo] Erreur HTTP pour station {station.id}: {exc}")
        return None

    if "hourly" not in data:
        logger.error(
            f"[OpenMeteo] Réponse inattendue pour station {station.id}: {data}"
        )
        return None

    hourly = data["hourly"]

    # Récupérer le dernier index valide (non-None) pour snow_depth
    snow_depths = hourly.get("snow_depth", [])
    times = hourly.get("time", [])

    current_idx = _get_current_hour_index(times)

    snow_depth_cm = _get_value_at(snow_depths, current_idx)
    # Open-Meteo retourne snow_depth en mètres → convertir en cm
    if snow_depth_cm is not None:
        snow_depth_cm = round(snow_depth_cm * 100, 1)

    snowfall_raw = _get_value_at(hourly.get("snowfall", []), current_idx)
    # Open-Meteo retourne snowfall en cm directement
    snowfall_cm = round(snowfall_raw, 1) if snowfall_raw is not None else None

    temperature = _get_value_at(hourly.get("temperature_2m", []), current_idx)
    temperature_c = round(temperature, 1) if temperature is not None else None

    precipitation_raw = _get_value_at(hourly.get("precipitation", []), current_idx)
    precipitation_mm = (
        round(precipitation_raw, 1) if precipitation_raw is not None else None
    )

    result = SnowData(
        station_id=station.id,
        latitude=lat,
        longitude=lng,
        fetched_at=datetime.now(tz=timezone.utc),
        snow_depth_cm=snow_depth_cm,
        snowfall_cm=snowfall_cm,
        temperature_c=temperature_c,
        precipitation_mm=precipitation_mm,
    )

    logger.info(f"[OpenMeteo] ✅ {result}")
    return result


def fetch_snow_for_all_stations() -> list[SnowData]:
    """
    Récupère les données de neige pour toutes les stations en base.

    Returns:
        Liste de SnowData (une par station, les erreurs sont ignorées)
    """
    # Import ici pour éviter les imports circulaires
    from stations.models import Station

    stations = Station.objects.all()
    results = []

    logger.info(f"[OpenMeteo] Récupération pour {stations.count()} stations...")

    for station in stations:
        data = fetch_snow_for_station(station)
        if data is not None:
            results.append(data)

    logger.info(f"[OpenMeteo] ✅ {len(results)}/{stations.count()} stations récupérées")
    return results


# ─── Helpers ────────────────────────────────────────────────────────────────


def _get_current_hour_index(times: list[str]) -> int:
    """
    Trouve l'index correspondant à l'heure courante UTC dans la liste de times.
    Si l'heure exacte n'est pas trouvée, retourne le dernier index disponible.

    Open-Meteo retourne des timestamps au format "2024-01-15T14:00"
    """
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:00")

    for i, t in enumerate(times):
        if t == now_str:
            return i

    # Fallback : dernier index non-None
    return len(times) - 1 if times else 0


def _get_value_at(values: list, index: int) -> Optional[float]:
    """
    Retourne la valeur à l'index donné, ou cherche en arrière
    le dernier index non-None si la valeur courante est None.
    """
    if not values:
        return None

    # Clamp l'index
    index = min(index, len(values) - 1)

    # Chercher en arrière si la valeur est None
    for i in range(index, -1, -1):
        if values[i] is not None:
            return float(values[i])

    return None
