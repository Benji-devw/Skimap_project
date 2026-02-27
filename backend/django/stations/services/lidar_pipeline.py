"""
Service de traitement LIDAR en arrière-plan (threads).

ARCHITECTURE : DTM INDÉPENDANT PAR UPLOAD
─────────────────────────────────────────
Chaque fichier LAZ uploadé produit ses propres fichiers :
    media/lidar/dtm_<station_id>_<upload_id>.tif
    media/lidar/dtm_<station_id>_<upload_id>_slope.tif
    media/lidar/dtm_<station_id>_<upload_id>_aspect.tif
    media/lidar/snow_classified_<station_id>_<upload_id>.tif

Le GeoJSON final fusionne les rasters classifiés de toutes les zones :
    media/lidar/snow_contours_<station_id>.geojson

Avantages :
- Supprimer une zone ne re-traite que les autres zones (pas de refusion LAZ)
- Ajouter une zone ne re-traite pas les zones existantes
- Chaque zone garde son propre DTM indépendant

PIPELINE DTM (déclenché à chaque upload de LAZ)
    → Génère DTM + slope + aspect pour CE LAZ uniquement
    → Met à jour LidarDTM en base
    → Lance automatiquement le pipeline neige

PIPELINE NEIGE (déclenché après chaque DTM ou manuellement)
    → Pour chaque upload de la station qui a un DTM prêt :
        → predict_snow_coverage → snow_classified_<station_id>_<upload_id>.tif
    → Fusionne tous les rasters classifiés → snow_contours_<station_id>.geojson
    → Met à jour LidarSnow en base

ANNULATION
    → cancel_pipeline(station_id) stoppe proprement le pipeline en cours
    → Tue le subprocess actif s'il y en a un
    → Met le statut à "error" en base
"""

import logging
import subprocess
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path("/app")
MEDIA_LIDAR = BASE_DIR / "media" / "lidar"

CREATE_DTM_SCRIPT = BASE_DIR / "create_dtm.py"
PREDICT_SCRIPT = BASE_DIR / "predict_snow_coverage.py"
CONVERT_SCRIPT = BASE_DIR / "convert_raster_to_geojson.py"

# ─── Registre d'annulation et verrous (par station_id) ───────────────────────
_cancel_events: dict[int, threading.Event] = {}
_active_procs: dict[int, subprocess.Popen] = {}  # type: ignore[type-arg]
_dtm_locks: dict[int, threading.Lock] = {}
_registry_lock = threading.Lock()

# ─── Registre de logs en mémoire (par station_id) ────────────────────────────
# Chaque entrée : {"ts": "HH:MM:SS", "level": "INFO"|"WARN"|"ERROR", "msg": "..."}
_pipeline_logs: dict[int, list[dict]] = {}
_logs_lock = threading.Lock()
MAX_LOG_LINES = 200  # nombre max de lignes gardées par station


def _log(station_id: int, msg: str, level: str = "INFO") -> None:
    """Ajoute une ligne de log pour une station et la propage au logger Python."""
    import datetime

    entry = {
        "ts": datetime.datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "msg": msg,
    }
    with _logs_lock:
        if station_id not in _pipeline_logs:
            _pipeline_logs[station_id] = []
        _pipeline_logs[station_id].append(entry)
        # Garder seulement les N dernières lignes
        if len(_pipeline_logs[station_id]) > MAX_LOG_LINES:
            _pipeline_logs[station_id] = _pipeline_logs[station_id][-MAX_LOG_LINES:]

    # Propager au logger Python standard (visible dans docker logs)
    if level == "ERROR":
        logger.error(msg)
    elif level == "WARN":
        logger.warning(msg)
    else:
        logger.info(msg)


def get_pipeline_logs(station_id: int) -> list[dict]:
    """Retourne une copie des logs en mémoire pour une station."""
    with _logs_lock:
        return list(_pipeline_logs.get(station_id, []))


def clear_pipeline_logs(station_id: int) -> None:
    """Vide les logs d'une station (appelé au démarrage d'un nouveau pipeline)."""
    with _logs_lock:
        _pipeline_logs[station_id] = []


# ─── Registre d'annulation ────────────────────────────────────────────────────


def _get_cancel_event(station_id: int) -> threading.Event:
    with _registry_lock:
        if station_id not in _cancel_events:
            _cancel_events[station_id] = threading.Event()
        return _cancel_events[station_id]


def _reset_cancel_event(station_id: int) -> None:
    with _registry_lock:
        _cancel_events[station_id] = threading.Event()


def _get_dtm_lock(station_id: int) -> threading.Lock:
    with _registry_lock:
        if station_id not in _dtm_locks:
            _dtm_locks[station_id] = threading.Lock()
        return _dtm_locks[station_id]


def dtm_pipeline_is_running(station_id: int) -> bool:
    lock = _get_dtm_lock(station_id)
    acquired = lock.acquire(blocking=False)
    if acquired:
        lock.release()
        return False
    return True


def _register_proc(station_id: int, proc: "subprocess.Popen[bytes]") -> None:
    with _registry_lock:
        _active_procs[station_id] = proc


def _unregister_proc(station_id: int) -> None:
    with _registry_lock:
        _active_procs.pop(station_id, None)


def cancel_pipeline(station_id: int) -> bool:
    """
    Annule le pipeline DTM ou neige en cours pour une station.
    Returns True si un pipeline était en cours.
    """
    event = _get_cancel_event(station_id)
    was_running = False

    with _registry_lock:
        proc = _active_procs.get(station_id)
        if proc is not None:
            was_running = True
            try:
                proc.kill()
                logger.info(f"[Cancel] Subprocess tué pour station id={station_id}")
            except Exception as exc:
                logger.warning(f"[Cancel] Impossible de tuer le proc : {exc}")

    event.set()

    try:
        from stations.models import LidarDTM, LidarSnow, Station

        station = Station.objects.get(pk=station_id)
        for Model in (LidarDTM, LidarSnow):
            try:
                record = Model.objects.get(station=station)  # type: ignore[attr-defined]
                if record.status in ("pending", "running"):
                    record.status = "error"
                    record.progress_step = "Annulé par l'utilisateur"
                    record.error_message = "Pipeline annulé manuellement"
                    record.save(
                        update_fields=["status", "progress_step", "error_message"]
                    )
                    was_running = True
            except Model.DoesNotExist:  # type: ignore[attr-defined]
                pass
    except Exception as exc:
        logger.error(f"[Cancel] Erreur mise à jour statut : {exc}")

    return was_running


# ─── Chemins des fichiers ─────────────────────────────────────────────────────


def dtm_path(station_id: int, upload_id: int) -> Path:
    """DTM d'un upload spécifique."""
    return MEDIA_LIDAR / f"dtm_{station_id}_{upload_id}.tif"


def slope_path(station_id: int, upload_id: int) -> Path:
    return MEDIA_LIDAR / f"dtm_{station_id}_{upload_id}_slope.tif"


def aspect_path(station_id: int, upload_id: int) -> Path:
    return MEDIA_LIDAR / f"dtm_{station_id}_{upload_id}_aspect.tif"


def snow_prediction_path(station_id: int, upload_id: int) -> Path:
    """Raster de prédiction brut (non classifié) d'un upload."""
    return MEDIA_LIDAR / f"snow_prediction_{station_id}_{upload_id}.tif"


def snow_classified_path(station_id: int, upload_id: int) -> Path:
    """
    Raster classifié produit par predict_snow_coverage.py avec --save-classified.
    Le script génère : output.replace('.tif', '_classified.tif')
    Donc si output = snow_prediction_3_9.tif → classifié = snow_prediction_3_9_classified.tif
    """
    return MEDIA_LIDAR / f"snow_prediction_{station_id}_{upload_id}_classified.tif"


def snow_geojson_path(station_id: int) -> Path:
    """GeoJSON final fusionné pour la station (toutes zones confondues)."""
    return MEDIA_LIDAR / f"snow_contours_{station_id}.geojson"


def upload_dtm_ready(station_id: int, upload_id: int) -> bool:
    """True si le DTM, slope et aspect existent pour cet upload."""
    return all(
        f.exists()
        for f in [
            dtm_path(station_id, upload_id),
            slope_path(station_id, upload_id),
            aspect_path(station_id, upload_id),
        ]
    )


def dtm_ready(station_id: int) -> bool:
    """
    True si au moins un upload de la station a un DTM prêt.
    Utilisé par l'endpoint snow/refresh pour vérifier qu'on peut calculer la neige.
    """
    try:
        from stations.models import LidarUpload, Station

        station = Station.objects.get(pk=station_id)
        uploads = LidarUpload.objects.filter(station=station)
        return any(upload_dtm_ready(station_id, u.id) for u in uploads)
    except Exception:
        return False


def station_files_for_upload(station_id: int, upload_id: int) -> list[Path]:
    """Tous les fichiers générés pour un upload donné."""
    return [
        dtm_path(station_id, upload_id),
        slope_path(station_id, upload_id),
        aspect_path(station_id, upload_id),
        snow_prediction_path(station_id, upload_id),
        snow_classified_path(station_id, upload_id),
    ]


# ─── Suppression d'un upload ─────────────────────────────────────────────────


def delete_laz_upload(upload_id: int) -> dict:
    """
    Supprime un LidarUpload (fichier LAZ + fichiers générés) et invalide
    le GeoJSON final de la station.

    Si d'autres uploads restent pour la station ET ont déjà un DTM prêt,
    re-génère uniquement le GeoJSON (merge des rasters existants) — très rapide.

    Si c'était le dernier upload, supprime aussi LidarDTM et LidarSnow.

    Returns:
        {
            "upload_id": int,
            "station_id": int,
            "file_deleted": bool,
            "remaining_laz": int,
            "pipeline_restarted": bool,
        }
    """
    from stations.models import LidarDTM, LidarSnow, LidarUpload

    try:
        upload = LidarUpload.objects.select_related("station").get(pk=upload_id)
    except LidarUpload.DoesNotExist:
        raise ValueError(f"LidarUpload id={upload_id} introuvable")

    station = upload.station
    station_id = station.id

    # Annuler tout pipeline en cours
    cancel_pipeline(station_id)

    # ── Supprimer le fichier LAZ source ───────────────────────────────────────
    file_deleted = False
    laz_disk_path = BASE_DIR / upload.laz_file.name
    if laz_disk_path.exists():
        try:
            laz_disk_path.unlink()
            file_deleted = True
            logger.info(f"[Delete LAZ] Supprimé : {laz_disk_path.name}")
        except Exception as exc:
            logger.warning(
                f"[Delete LAZ] Impossible de supprimer {laz_disk_path.name} : {exc}"
            )

    # ── Supprimer les fichiers générés pour CET upload ───────────────────────
    for f in station_files_for_upload(station_id, upload_id):
        if f.exists():
            try:
                f.unlink()
                logger.info(f"[Delete LAZ] Supprimé : {f.name}")
            except Exception as exc:
                logger.warning(f"[Delete LAZ] Impossible de supprimer {f.name} : {exc}")

    # Supprimer l'enregistrement DB
    upload.delete()
    logger.info(f"[Delete LAZ] LidarUpload id={upload_id} supprimé")

    # ── Invalider le GeoJSON final (il doit être régénéré) ────────────────────
    geojson = snow_geojson_path(station_id)
    if geojson.exists():
        try:
            geojson.unlink()
        except Exception:
            pass

    # ── Compter les uploads restants ──────────────────────────────────────────
    from stations.models import LidarUpload as LU

    remaining_uploads = list(LU.objects.filter(station=station))
    remaining_laz = len(remaining_uploads)
    pipeline_restarted = False

    if remaining_laz == 0:
        # Plus aucun LAZ — tout nettoyer
        LidarDTM.objects.filter(station=station).delete()
        LidarSnow.objects.filter(station=station).delete()
        logger.info(
            f"[Delete LAZ] Plus aucun LAZ pour '{station.nom}' — DB réinitialisée"
        )
    else:
        # Vérifier si certains uploads ont déjà un DTM prêt
        ready_uploads = [
            u for u in remaining_uploads if upload_dtm_ready(station_id, u.id)
        ]

        if ready_uploads:
            # On peut régénérer le GeoJSON directement sans refaire les DTM
            # Mettre à jour le compteur et relancer le pipeline neige (merge only)
            LidarDTM.objects.filter(station=station).update(
                status="done",
                progress_step=f"{len(ready_uploads)} zone(s) disponible(s)",
                error_message="",
                laz_count=len(ready_uploads),
            )
            _reset_cancel_event(station_id)
            run_snow_pipeline_async(station_id)
            pipeline_restarted = True
            logger.info(
                f"[Delete LAZ] {len(ready_uploads)} DTM restant(s) pour '{station.nom}' — "
                f"pipeline neige relancé (merge uniquement)"
            )
        else:
            # Des uploads restent mais aucun DTM prêt — relancer le pipeline DTM complet
            # pour les uploads qui n'ont pas encore de DTM
            pending_uploads = [
                u for u in remaining_uploads if not upload_dtm_ready(station_id, u.id)
            ]
            if pending_uploads:
                LidarDTM.objects.filter(station=station).update(
                    status="pending",
                    progress_step="En attente de traitement…",
                    error_message="",
                    laz_count=remaining_laz,
                )
                _reset_cancel_event(station_id)
                # Lancer le DTM pour le premier upload en attente
                run_dtm_pipeline_async(station_id)
                pipeline_restarted = True

    return {
        "upload_id": upload_id,
        "station_id": station_id,
        "file_deleted": file_deleted,
        "remaining_laz": remaining_laz,
        "pipeline_restarted": pipeline_restarted,
    }


# ─── Pipeline DTM ─────────────────────────────────────────────────────────────


def run_dtm_pipeline_async(station_id: int) -> bool:
    """
    Lance le pipeline DTM dans un thread séparé.
    Traite uniquement les uploads qui n'ont pas encore de DTM.
    Une fois terminé, lance automatiquement le pipeline neige.

    Returns True si le pipeline a été lancé, False si déjà en cours.
    """
    if dtm_pipeline_is_running(station_id):
        logger.warning(
            f"[DTM Pipeline] Pipeline déjà en cours pour station id={station_id}, ignoré"
        )
        return False

    _reset_cancel_event(station_id)
    thread = threading.Thread(
        target=_run_dtm_pipeline,
        args=(station_id,),
        daemon=True,
    )
    thread.start()
    logger.info(f"[DTM Pipeline] Thread démarré pour station id={station_id}")
    return True


def _run_dtm_pipeline(station_id: int) -> None:
    dtm_lock = _get_dtm_lock(station_id)
    cancel_event = _get_cancel_event(station_id)

    if not dtm_lock.acquire(blocking=False):
        logger.warning(
            f"[DTM Pipeline] Verrou déjà pris pour station id={station_id}, abandon"
        )
        return

    try:
        _run_dtm_pipeline_locked(station_id, cancel_event, dtm_lock)
    finally:
        if dtm_lock.locked():
            dtm_lock.release()


def _run_dtm_pipeline_locked(
    station_id: int,
    cancel_event: threading.Event,
    dtm_lock: threading.Lock,
) -> None:
    """
    Pipeline DTM par upload :
    Pour chaque LidarUpload de la station qui n'a PAS encore de DTM :
        1. Génère dtm_<station_id>_<upload_id>.tif + slope + aspect
    Lance ensuite le pipeline neige.
    """
    from django.utils import timezone

    from stations.models import LidarDTM, LidarUpload, Station

    try:
        station = Station.objects.get(pk=station_id)
    except Station.DoesNotExist:
        logger.error(f"[DTM Pipeline] Station id={station_id} introuvable")
        return

    dtm_record, _ = LidarDTM.objects.get_or_create(
        station=station,
        defaults={"status": "pending"},
    )

    def _set_status(status: str, step: str = "", error: str = "") -> None:
        dtm_record.status = status
        dtm_record.progress_step = step
        if error:
            dtm_record.error_message = error
        if status == "running" and not dtm_record.started_at:
            dtm_record.started_at = timezone.now()
        if status == "done":
            dtm_record.completed_at = timezone.now()
        dtm_record.save(
            update_fields=[
                "status",
                "progress_step",
                "error_message",
                "started_at",
                "completed_at",
                "laz_count",
            ]
        )

    _set_status("running", "Démarrage du pipeline DTM…")

    if cancel_event.is_set():
        _set_status("error", "Annulé par l'utilisateur", "Annulé avant démarrage")
        return

    # ── Trouver les uploads sans DTM ─────────────────────────────────────────
    all_uploads = list(
        LidarUpload.objects.filter(station=station).order_by("uploaded_at")
    )

    if not all_uploads:
        _set_status(
            "error", "Aucun fichier LAZ trouvé", "Uploadez au moins un fichier LAZ"
        )
        logger.error(f"[DTM Pipeline] Aucun LAZ pour station '{station.nom}'")
        return

    # Uploads qui ont besoin d'un DTM (pas encore généré ou fichiers manquants)
    pending_uploads = [u for u in all_uploads if not upload_dtm_ready(station_id, u.id)]

    already_ready = len(all_uploads) - len(pending_uploads)
    logger.info(
        f"[DTM Pipeline] Station '{station.nom}' : "
        f"{len(pending_uploads)} upload(s) à traiter, {already_ready} déjà prêt(s)"
    )

    if not pending_uploads:
        # Tous les DTM sont déjà là, rien à faire
        total_ready = len(all_uploads)
        dtm_record.laz_count = total_ready
        _set_status("done", f"DTM prêt ({total_ready} zone(s))")
        dtm_lock.release()
        run_snow_pipeline_async(station_id)
        return

    dtm_record.laz_count = len(all_uploads)
    errors = []

    # ── Générer un DTM par upload en attente ─────────────────────────────────
    for i, upload in enumerate(pending_uploads, 1):
        if cancel_event.is_set():
            _set_status(
                "error", "Annulé par l'utilisateur", "Annulé pendant la génération DTM"
            )
            return

        laz_file = BASE_DIR / upload.laz_file.name
        if not laz_file.exists():
            logger.warning(
                f"[DTM Pipeline] Fichier LAZ manquant : {laz_file.name} — ignoré"
            )
            errors.append(f"{upload.original_filename} : fichier manquant")
            continue

        step = (
            f"Zone {i}/{len(pending_uploads)} — "
            f"{upload.original_filename or laz_file.name}…"
        )
        _set_status("running", f"Génération DTM : {step}")
        logger.info(
            f"[DTM Pipeline] Génération DTM pour upload id={upload.id} : {laz_file.name}"
        )

        dtm_out = dtm_path(station_id, upload.id)
        create_dtm_cmd = [
            sys.executable,
            str(CREATE_DTM_SCRIPT),
            "--input",
            str(laz_file),
            "--output",
            str(dtm_out),
            "--resolution",
            "2.0",
            "--calculate-slope",
            "--calculate-aspect",
            "--quiet",
        ]

        ok, err = _run(create_dtm_cmd, station_id)
        if not ok:
            if cancel_event.is_set():
                _set_status(
                    "error", "Annulé par l'utilisateur", "Génération DTM annulée"
                )
                return
            logger.error(
                f"[DTM Pipeline] create_dtm échoué pour upload id={upload.id} : {err}"
            )
            errors.append(f"{upload.original_filename} : {err[:120]}")
            continue

        # Vérifier que les 3 fichiers ont été produits
        missing = [
            f
            for f in [
                dtm_out,
                slope_path(station_id, upload.id),
                aspect_path(station_id, upload.id),
            ]
            if not f.exists()
        ]
        if missing:
            msg = f"Fichiers manquants après génération : {', '.join(f.name for f in missing)}"
            logger.error(f"[DTM Pipeline] {msg}")
            errors.append(f"{upload.original_filename} : {msg}")
            continue

        logger.info(f"[DTM Pipeline] ✅ DTM généré → {dtm_out.name}")

    # ── Bilan ─────────────────────────────────────────────────────────────────
    total_ready = sum(1 for u in all_uploads if upload_dtm_ready(station_id, u.id))
    dtm_record.laz_count = total_ready

    if total_ready == 0:
        err_summary = " | ".join(errors) if errors else "Aucun DTM généré"
        _set_status("error", "Échec de la génération DTM", err_summary)
        logger.error(f"[DTM Pipeline] Aucun DTM disponible pour '{station.nom}'")
        return

    if errors:
        logger.warning(
            f"[DTM Pipeline] {total_ready}/{len(all_uploads)} DTM générés "
            f"pour '{station.nom}' ({len(errors)} erreur(s))"
        )
    else:
        logger.info(f"[DTM Pipeline] ✅ {total_ready} DTM générés pour '{station.nom}'")

    _set_status("done", f"DTM prêt ({total_ready} zone(s))")
    logger.info(f"[DTM Pipeline] ✅ Pipeline DTM terminé pour '{station.nom}'")

    # Libérer le verrou avant de lancer le pipeline neige
    dtm_lock.release()

    if cancel_event.is_set():
        logger.info(f"[DTM Pipeline] Annulé — pipeline neige non lancé")
        return

    logger.info(f"[DTM Pipeline] Lancement automatique du pipeline neige…")
    run_snow_pipeline_async(station_id)


# ─── Pipeline Neige ───────────────────────────────────────────────────────────


def run_snow_pipeline_async(station_id: int) -> None:
    """Lance le pipeline neige dans un thread séparé."""
    _reset_cancel_event(station_id)
    thread = threading.Thread(
        target=_run_snow_pipeline,
        args=(station_id,),
        daemon=True,
    )
    thread.start()
    logger.info(f"[Snow Pipeline] Thread démarré pour station id={station_id}")


def _run_snow_pipeline(station_id: int) -> None:
    """
    Pipeline neige par upload :
    1. Récupère la hauteur de neige depuis Open-Meteo (une seule fois)
    2. Pour chaque upload avec DTM prêt :
       → predict_snow_coverage → snow_classified_<station_id>_<upload_id>.tif
    3. Fusionne tous les rasters classifiés en un seul GeoJSON
    """
    from django.utils import timezone

    from stations.models import LidarSnow, LidarUpload, SnowMeasure, Station
    from stations.services.open_meteo import fetch_snow_for_station

    cancel_event = _get_cancel_event(station_id)

    try:
        station = Station.objects.get(pk=station_id)
    except Station.DoesNotExist:
        logger.error(f"[Snow Pipeline] Station id={station_id} introuvable")
        return

    snow_record, _ = LidarSnow.objects.get_or_create(
        station=station,
        defaults={"status": "none"},
    )

    def _set_status(status: str, step: str = "", error: str = "") -> None:
        snow_record.status = status
        snow_record.progress_step = step
        if error:
            snow_record.error_message = error
        if status == "running" and not snow_record.started_at:
            snow_record.started_at = timezone.now()
        if status == "done":
            snow_record.completed_at = timezone.now()
        snow_record.save(
            update_fields=[
                "status",
                "progress_step",
                "error_message",
                "base_snow_cm",
                "started_at",
                "completed_at",
            ]
        )

    _set_status("running", "Démarrage du pipeline neige…")

    # ── Récupérer les uploads avec DTM prêt ───────────────────────────────────
    all_uploads = list(
        LidarUpload.objects.filter(station=station).order_by("uploaded_at")
    )
    ready_uploads = [u for u in all_uploads if upload_dtm_ready(station_id, u.id)]

    if not ready_uploads:
        msg = "Aucun DTM disponible. Uploadez d'abord un fichier LAZ."
        _set_status("error", msg, msg)
        logger.error(f"[Snow Pipeline] {msg} (station id={station_id})")
        return

    logger.info(
        f"[Snow Pipeline] {len(ready_uploads)} zone(s) avec DTM prêt pour '{station.nom}'"
    )

    # ── Étape 1 : Open-Meteo (une seule fois pour toute la station) ───────────
    _set_status("running", "Récupération de la hauteur de neige (Open-Meteo)…")

    snow_data = fetch_snow_for_station(station)

    if snow_data is None or snow_data.snow_depth_cm is None:
        base_snow_cm = 75.0
        logger.warning(
            f"[Snow Pipeline] Open-Meteo indisponible, fallback sur {base_snow_cm} cm"
        )
    else:
        base_snow_cm = snow_data.snow_depth_cm
        logger.info(f"[Snow Pipeline] Hauteur de neige réelle : {base_snow_cm} cm")

    snow_record.base_snow_cm = base_snow_cm
    snow_record.save(update_fields=["base_snow_cm"])

    base_elevation = _estimate_base_elevation(station)
    errors = []

    # ── Étape 2 : Prédiction par upload ───────────────────────────────────────
    for i, upload in enumerate(ready_uploads, 1):
        if cancel_event.is_set():
            _set_status(
                "error", "Annulé par l'utilisateur", "Annulé pendant la prédiction"
            )
            return

        _set_status(
            "running",
            f"Prédiction zone {i}/{len(ready_uploads)} — "
            f"{upload.original_filename or f'zone {upload.id}'}…",
        )

        predict_cmd = [
            sys.executable,
            str(PREDICT_SCRIPT),
            "--dtm",
            str(dtm_path(station_id, upload.id)),
            "--slope",
            str(slope_path(station_id, upload.id)),
            "--aspect",
            str(aspect_path(station_id, upload.id)),
            "--output",
            str(snow_prediction_path(station_id, upload.id)),
            "--base-snow",
            str(base_snow_cm),
            "--base-elevation",
            str(base_elevation),
            "--save-classified",
            "--quiet",
        ]

        ok, err = _run(predict_cmd, station_id)
        if not ok:
            if cancel_event.is_set():
                _set_status("error", "Annulé par l'utilisateur", "Prédiction annulée")
                return
            logger.error(
                f"[Snow Pipeline] predict_snow échoué pour upload id={upload.id} : {err}"
            )
            errors.append(f"{upload.original_filename} : {err[:120]}")
            continue

        # Vérifier que le raster classifié a bien été produit
        classified = snow_classified_path(station_id, upload.id)
        if not classified.exists():
            msg = f"Raster classifié manquant après prédiction : {classified.name}"
            logger.error(f"[Snow Pipeline] {msg}")
            errors.append(msg)
            continue

        logger.info(f"[Snow Pipeline] ✅ Prédiction zone {i} → {classified.name}")

    # Vérifier qu'on a au moins un raster classifié
    classified_rasters = [
        snow_classified_path(station_id, u.id)
        for u in ready_uploads
        if snow_classified_path(station_id, u.id).exists()
    ]

    if not classified_rasters:
        err_summary = " | ".join(errors) if errors else "Aucun raster généré"
        _set_status("error", "Échec de la prédiction", err_summary)
        logger.error(f"[Snow Pipeline] Aucun raster classifié pour '{station.nom}'")
        return

    # ── Étape 3 : Fusion des rasters classifiés + GeoJSON ────────────────────
    if cancel_event.is_set():
        _set_status(
            "error", "Annulé par l'utilisateur", "Annulé avant conversion GeoJSON"
        )
        return

    _set_status("running", "Conversion en GeoJSON pour la carte…")

    if len(classified_rasters) == 1:
        # Un seul raster — conversion directe
        merged_classified = classified_rasters[0]
    else:
        # Plusieurs rasters — fusion avec rasterio avant conversion
        _set_status("running", f"Fusion de {len(classified_rasters)} zones…")
        merged_classified = MEDIA_LIDAR / f"snow_classified_merged_{station_id}.tif"
        ok, err = _merge_classified_rasters(classified_rasters, merged_classified)
        if not ok:
            _set_status("error", "Échec de la fusion des zones", err)
            logger.error(f"[Snow Pipeline] Fusion rasters échouée : {err}")
            return
        logger.info(f"[Snow Pipeline] Rasters fusionnés → {merged_classified.name}")
        _set_status("running", "Conversion en GeoJSON pour la carte…")

    geojson_out = snow_geojson_path(station_id)
    convert_cmd = [
        sys.executable,
        str(CONVERT_SCRIPT),
        "--input",
        str(merged_classified),
        "--output",
        str(geojson_out),
        "--simplify",
        "10",
        "--quiet",
    ]

    if cancel_event.is_set():
        _set_status(
            "error", "Annulé par l'utilisateur", "Annulé avant conversion GeoJSON"
        )
        return

    ok, err = _run(convert_cmd, station_id)

    # Nettoyage du raster de fusion temporaire
    if len(classified_rasters) > 1 and merged_classified.exists():
        try:
            merged_classified.unlink()
        except Exception:
            pass

    if not ok:
        if cancel_event.is_set():
            _set_status(
                "error", "Annulé par l'utilisateur", "Conversion GeoJSON annulée"
            )
        else:
            _set_status("error", "Échec de la conversion GeoJSON", err)
        logger.error(f"[Snow Pipeline] convert_raster échoué : {err}")
        return

    geojson_size = geojson_out.stat().st_size / 1024
    logger.info(
        f"[Snow Pipeline] GeoJSON généré → {geojson_out.name} ({geojson_size:.1f} Ko)"
    )

    # ── Sauvegarde SnowMeasure ────────────────────────────────────────────────
    if snow_data is not None:
        SnowMeasure.objects.create(
            station=station,
            date_time=snow_data.fetched_at,
            temperature_c=snow_data.temperature_c,
            precipitation_mm=snow_data.precipitation_mm,
            total_snow_height_cm=snow_data.snow_depth_cm,
            natural_snow_height_cm=snow_data.snow_depth_cm,
            artificial_snow_height_cm=None,
            artificial_snow_production_m3=None,
        )

    n = len(classified_rasters)
    suffix = f"{n} zone(s)" if n > 1 else "1 zone"
    _set_status(
        "done",
        f"Carte de neige prête — {base_snow_cm} cm (Open-Meteo) · {suffix}",
    )
    logger.info(f"[Snow Pipeline] ✅ Pipeline neige terminé pour '{station.nom}'")


# ─── Fusion rasters classifiés ────────────────────────────────────────────────


def _merge_classified_rasters(
    raster_paths: list[Path],
    output: Path,
) -> tuple[bool, str]:
    """
    Fusionne plusieurs rasters classifiés (0-5) en un seul en utilisant rasterio.merge.
    En cas de chevauchement, prend la valeur maximale (plus de neige gagne).
    Beaucoup plus rapide que la fusion LAZ car on travaille sur des pixels, pas des points.
    """
    try:
        import rasterio
        from rasterio.merge import merge as rasterio_merge

        datasets = [rasterio.open(str(p)) for p in raster_paths]

        try:
            merged_data, merged_transform = rasterio_merge(
                datasets,
                method="max",  # En cas de chevauchement, on prend la valeur max
            )
        finally:
            for ds in datasets:
                ds.close()

        # Copier le profil du premier raster et ajuster les dimensions
        profile = rasterio.open(str(raster_paths[0])).meta.copy()
        profile.update(
            height=merged_data.shape[1],
            width=merged_data.shape[2],
            transform=merged_transform,
            compress="lzw",
        )

        with rasterio.open(str(output), "w", **profile) as dst:
            dst.write(merged_data)

        logger.info(
            f"[Merge Rasters] {len(raster_paths)} rasters → {output.name} "
            f"({output.stat().st_size // 1024} Ko)"
        )
        return True, ""

    except ImportError:
        return False, "rasterio non installé"
    except Exception as exc:
        return False, str(exc)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _run(
    cmd: list[str],
    station_id: int | None = None,
) -> tuple[bool, str]:
    """
    Exécute une commande subprocess.
    Si station_id est fourni, enregistre le process pour permettre l'annulation.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(BASE_DIR),
        )

        if station_id is not None:
            _register_proc(station_id, proc)

        stdout, stderr = proc.communicate()

        if station_id is not None:
            _unregister_proc(station_id)

        if proc.returncode != 0:
            if proc.returncode in (-9, -15):
                return False, "Processus tué (annulation)"
            return (
                False,
                stderr.decode(errors="replace")
                or stdout.decode(errors="replace")
                or f"Code retour {proc.returncode}",
            )
        return True, ""
    except Exception as exc:
        if station_id is not None:
            _unregister_proc(station_id)
        return False, str(exc)


def _estimate_base_elevation(station) -> float:
    """Altitude de référence pour le modèle de neige (1500m pour les Alpes)."""
    return 1500.0
