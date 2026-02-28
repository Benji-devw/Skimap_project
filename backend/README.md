# 🏔️ Backend SkiMap - API Django + Traitement LIDAR

## 📋 Vue d'ensemble

Backend Django REST avec PostGIS pour la gestion des stations de ski, pistes, mesures de neige et traitement de données LIDAR pour prédiction d'accumulation de neige.

---

## 🏗️ Architecture

```
backend/
├── db/
│   ├── init.sql                 # Schéma PostgreSQL initial + données
│   └── fix_sequences.sql        # Fix des séquences auto-increment
│
└── django/
    ├── skimap_backend/          # Configuration Django
    │   ├── settings.py          # Configuration principale
    │   ├── urls.py              # Routes API
    │   └── wsgi.py              # WSGI entry point
    │
    ├── stations/                # App principale
    │   ├── models.py            # Station, Piste, SnowMeasure
    │   ├── views.py             # ViewSets + endpoints LIDAR
    │   ├── serializers.py       # Sérialisation GeoJSON
    │   └── admin.py             # Interface d'administration
    │
    ├── lidar_processing/        # Module LIDAR
    │   ├── __init__.py
    │   ├── apps.py
    │   └── management/commands/
    │       ├── __init__.py
    │       └── explore_lidar.py # Django command analyse LIDAR
    │
    ├── media/lidar/             # Données LIDAR traitées
    │   ├── *.laz                # Fichiers LIDAR source
    │   ├── dtm_*.tif            # Modèles Numériques de Terrain
    │   ├── snow_prediction.tif  # Prédiction neige
    │   └── snow_contours.geojson # GeoJSON pour Mapbox
    │
    ├── analyze_lidar.py         # Script analyse fichiers LAZ
    ├── create_dtm.py            # Génération MNT + pente + exposition
    ├── predict_snow_coverage.py # Modèle prédiction neige
    ├── convert_raster_to_geojson.py # Conversion raster → GeoJSON
    │
    ├── requirements.txt         # Dépendances Python
    └── manage.py                # Django CLI
```

---

## 🚀 Installation

### Étape 1 - Lancer avec Docker (Recommandé)

```bash
# Depuis la racine du projet
cd Skimap_project
docker compose up -d --build
```

**Services démarrés :**

- PostgreSQL PostGIS : `localhost:5432`
- Django API : `http://localhost:8000`

### Étape 2 - Installation locale (Alternative)

```bash
cd backend/django

# Créer environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Installer dépendances
pip install -r requirements.txt

# Installer dépendances système (Mac)
brew install gdal geos pdal

# Installer dépendances système (Ubuntu)
sudo apt-get install gdal-bin libgdal-dev libgeos-dev
```

### Étape 3 - Configuration Base de Données

```bash
# Avec Docker (automatique via init.sql)
docker compose up -d

# Sans Docker (manuel)
psql -U postgres
CREATE DATABASE skimap;
CREATE EXTENSION postgis;
\c skimap
\i ../db/init.sql
```

### Étape 4 - Migrations Django

```bash
# Avec Docker
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Sans Docker
python manage.py makemigrations
python manage.py migrate
```

### Étape 5 - Démarrer le serveur

```bash
# Avec Docker (déjà démarré)
docker compose up -d

# Sans Docker
python manage.py runserver 0.0.0.0:8000
```

---

## 📡 API Endpoints

### Health Check

```bash
curl http://localhost:8000/health/
# → {"status": "ok"}
```

### Stations

| Méthode  | URL                                | Description                    |
| -------- | ---------------------------------- | ------------------------------ |
| `GET`    | `/api/stations/`                   | Liste toutes les stations      |
| `POST`   | `/api/stations/`                   | Créer une station              |
| `GET`    | `/api/stations/{id}/`              | Détails d'une station          |
| `PUT`    | `/api/stations/{id}/`              | Mettre à jour une station      |
| `DELETE` | `/api/stations/{id}/`              | Supprimer une station          |
| `GET`    | `/api/stations/{id}/snow_measures` | Mesures de neige d'une station |
| `POST`   | `/api/stations/{id}/snow_measures` | Ajouter une mesure de neige    |

**Exemple GET :**

```bash
curl http://localhost:8000/api/stations/ | jq
```

**Exemple POST :**

```bash
curl -X POST http://localhost:8000/api/stations/ \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Isola 2000",
    "geometry": {
      "type": "Point",
      "coordinates": [6.201809, 44.620601]
    }
  }'
```

### Pistes

| Méthode  | URL                            | Description             |
| -------- | ------------------------------ | ----------------------- |
| `GET`    | `/api/pistes/`                 | Liste toutes les pistes |
| `GET`    | `/api/pistes/?station_id={id}` | Pistes d'une station    |
| `POST`   | `/api/pistes/`                 | Créer une piste         |
| `GET`    | `/api/pistes/{id}/`            | Détails d'une piste     |
| `PUT`    | `/api/pistes/{id}/`            | Mettre à jour une piste |
| `DELETE` | `/api/pistes/{id}/`            | Supprimer une piste     |

**Exemple GET avec filtre :**

```bash
curl "http://localhost:8000/api/pistes/?station_id=1" | jq
```

**Exemple POST :**

```bash
curl -X POST http://localhost:8000/api/pistes/ \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Piste Verte",
    "station_id": 1,
    "type": "verte",
    "etat": "ouverte",
    "longueur": 1200,
    "geometry": {
      "type": "LineString",
      "coordinates": [[6.2, 44.62], [6.21, 44.61]]
    }
  }'
```

### Mesures de Neige

| Méthode  | URL                        | Description              |
| -------- | -------------------------- | ------------------------ |
| `GET`    | `/api/snow_measures/`      | Liste toutes les mesures |
| `POST`   | `/api/snow_measures/`      | Créer une mesure         |
| `GET`    | `/api/snow_measures/{id}/` | Détails d'une mesure     |
| `PUT`    | `/api/snow_measures/{id}/` | Mettre à jour une mesure |
| `DELETE` | `/api/snow_measures/{id}/` | Supprimer une mesure     |

**Exemple POST :**

```bash
curl -X POST http://localhost:8000/api/snow_measures/ \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": 1,
    "date_time": "2025-01-15T10:00:00Z",
    "temperature_c": -5.5,
    "precipitation_mm": 12.3,
    "total_snow_height_cm": 75.0,
    "natural_snow_height_cm": 60.0,
    "artificial_snow_height_cm": 15.0,
    "artificial_snow_production_m3": 250.0
  }'
```

### Endpoints LIDAR (NOUVEAU) ❄️

| Méthode | URL                                       | Description                  |
| ------- | ----------------------------------------- | ---------------------------- |
| `GET`   | `/api/snow-coverage/`                     | GeoJSON complet couche neige |
| `GET`   | `/api/snow-at-point/?lat={lat}&lng={lng}` | Hauteur neige à un point     |

**Exemple GET snow-coverage :**

```bash
curl http://localhost:8000/api/snow-coverage/ | jq
```

**Exemple GET snow-at-point :**

```bash
curl "http://localhost:8000/api/snow-at-point/?lat=44.602&lng=6.220" | jq
```

**Réponse :**

```json
{
    "snow_height_cm": 68.5,
    "category": "Moyen",
    "color": "#66FF66",
    "range": "50-80 cm",
    "description": "Bonnes conditions"
}
```

---

## 🔬 Traitement LIDAR

### Pipeline Complet

```bash
# Entrer dans le conteneur Django
docker exec -it skimap-django bash

# OU depuis votre machine si Python est installé localement
cd backend/django
source .venv/bin/activate
```

### 1. Analyser un fichier LIDAR

```bash
python analyze_lidar.py media/lidar/LHD_FXX_0955_6395_PTS_LAMB93_IGN69.copc.laz
```

**Résultat :**

- Nombre de points
- Emprise géographique (bbox)
- Classification des points (sol, végétation, bâtiments)
- Système de coordonnées (CRS)
- Statistiques d'altitude

### 2. Créer le MNT (Modèle Numérique de Terrain)

```bash
python create_dtm.py \
  --input media/lidar/LHD_FXX_0955_6395_PTS_LAMB93_IGN69.copc.laz \
  --output media/lidar/dtm_coste_belle.tif \
  --resolution 2.0 \
  --calculate-slope \
  --calculate-aspect
```

**Options :**

- `--resolution` : Résolution en mètres par pixel (défaut: 1.0)
- `--calculate-slope` : Calculer la pente
- `--calculate-aspect` : Calculer l'exposition
- `--method` : Méthode d'interpolation (linear, nearest, cubic)

**Fichiers générés :**

- `dtm_coste_belle.tif` - Altitude (MNT)
- `dtm_coste_belle_slope.tif` - Pente (0-90°)
- `dtm_coste_belle_aspect.tif` - Exposition (0-360°)

### 3. Prédire l'accumulation de neige

```bash
# Avec données réelles Open-Meteo (recommandé)
python predict_snow_coverage.py \
  --dtm media/lidar/dtm_coste_belle.tif \
  --slope media/lidar/dtm_coste_belle_slope.tif \
  --aspect media/lidar/dtm_coste_belle_aspect.tif \
  --output media/lidar/snow_prediction.tif \
  --lat 44.602 --lon 6.220 \
  --base-elevation 1600 \
  --save-classified

# Ou avec une valeur manuelle (sans connexion)
python predict_snow_coverage.py \
  --dtm media/lidar/dtm_coste_belle.tif \
  --slope media/lidar/dtm_coste_belle_slope.tif \
  --aspect media/lidar/dtm_coste_belle_aspect.tif \
  --output media/lidar/snow_prediction.tif \
  --base-snow 75 \
  --base-elevation 1600 \
  --save-classified
```

**Options :**

- `--lat` / `--lon` : Coordonnées WGS84 de la station → récupère la hauteur de neige réelle depuis Open-Meteo
- `--base-snow` : Hauteur de neige manuelle en cm (fallback si pas de connexion)
- `--base-elevation` : Altitude de référence en mètres
- `--save-classified` : Sauvegarder la version classifiée (0-5)

**Modèle d'accumulation :**

```
neige_prédite = neige_base ×
                facteur_altitude ×
                facteur_pente ×
                facteur_exposition ×
                facteur_vent

Où :
- facteur_altitude  = 1.0 + (altitude - base) / 1000
- facteur_pente     = 1.0 si <25°, réduction progressive >25°
- facteur_exposition = 0.7 (sud) → 1.2 (nord)
- facteur_vent      = 0.6 sur crêtes exposées
```

**Fichiers générés :**

- `snow_prediction.tif` - Hauteur neige continue (cm)
- `snow_prediction_classified.tif` - Classé 0-5

### 4. Convertir en GeoJSON pour Mapbox

```bash
python convert_raster_to_geojson.py \
  --input media/lidar/snow_prediction_classified.tif \
  --output media/lidar/snow_contours.geojson \
  --simplify 10
```

**Options :**

- `--simplify` : Tolérance de simplification en mètres (défaut: 10)
- `--no-simplify` : Ne pas simplifier les géométries

**Résultat :**

- Fichier GeoJSON avec 5 features (une par catégorie)
- Polygones simplifiés pour performance web
- Coordonnées converties en WGS84 (EPSG:4326)
- Propriétés : name, color, snow_range, description

---

## 🗄️ Modèles Django

### Station

```python
class Station(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    geometry = models.PointField(srid=4326, db_column='geom')
```

### Piste

```python
class Piste(models.Model):
    id = models.AutoField(primary_key=True)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    nom = models.CharField(max_length=255)
    type = models.CharField(max_length=50)  # verte, bleue, rouge, noire
    etat = models.CharField(max_length=50)  # ouverte, fermée
    longueur = models.IntegerField()  # en mètres
    geometry = models.LineStringField(srid=4326, db_column='geom')
```

### SnowMeasure

```python
class SnowMeasure(models.Model):
    id = models.AutoField(primary_key=True)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    temperature_c = models.DecimalField(max_digits=5, decimal_places=2)
    precipitation_mm = models.DecimalField(max_digits=6, decimal_places=2)
    total_snow_height_cm = models.DecimalField(max_digits=6, decimal_places=2)
    natural_snow_height_cm = models.DecimalField(max_digits=6, decimal_places=2)
    artificial_snow_height_cm = models.DecimalField(max_digits=6, decimal_places=2)
    artificial_snow_production_m3 = models.DecimalField(max_digits=10, decimal_places=2)
```

---

## 📦 Dépendances

### requirements.txt

```txt
django==5.2.6
djangorestframework
psycopg2-binary
django-cors-headers

# Traitement LIDAR
laspy==2.7.0          # Lecture fichiers LAZ/LAS
numpy==2.4.2          # Calculs numériques
scipy==1.17.0         # Interpolation
rasterio==1.4.4       # Manipulation rasters GeoTIFF
shapely==2.1.2        # Géométries et simplification
pyproj==3.7.2         # Transformations coordonnées
```

### Installation manuelle LIDAR

```bash
# Avec Docker
docker exec skimap-django pip install laspy numpy scipy rasterio shapely pyproj

# Sans Docker
pip install laspy numpy scipy rasterio shapely pyproj
```

---

## 🧪 Tests

### Test API

```bash
# Health check
curl http://localhost:8000/health/

# Stations
curl http://localhost:8000/api/stations/ | jq

# Pistes d'une station
curl "http://localhost:8000/api/pistes/?station_id=1" | jq

# Mesures de neige
curl http://localhost:8000/api/snow_measures/ | jq

# Couche de neige LIDAR
curl http://localhost:8000/api/snow-coverage/ | jq '.features | length'

# Point spécifique
curl "http://localhost:8000/api/snow-at-point/?lat=44.602&lng=6.220" | jq
```

### Test Base de Données

```bash
# Connexion PostgreSQL
docker exec -it skimap-postgis psql -U postgres -d skimap

# Requêtes de test
\dt                              # Liste tables
SELECT COUNT(*) FROM stations;   # Nombre stations
SELECT COUNT(*) FROM pistes;     # Nombre pistes
SELECT * FROM stations LIMIT 5;  # Premières stations

# Test spatial
SELECT nom, ST_AsText(geom) FROM stations LIMIT 3;
SELECT nom, ST_Length(geom) FROM pistes LIMIT 3;
```

---

## 🐛 Dépannage

### Erreur : "No module named 'laspy'"

```bash
docker exec skimap-django pip install laspy numpy scipy rasterio shapely pyproj
docker compose restart web
```

### Erreur : "Source mapbox-dem not found"

Le terrain 3D Mapbox nécessite un token valide.  
Vérifier : `frontend/.env` → `VITE_MAPBOX_TOKEN`

### Erreur : "Fichier snow_contours.geojson introuvable"

```bash
# Régénérer le GeoJSON
docker exec skimap-django python convert_raster_to_geojson.py \
  --input media/lidar/snow_prediction_classified.tif \
  --output media/lidar/snow_contours.geojson
```

### Base de données vide

```bash
# Réinitialiser
docker compose down -v
docker compose up -d

# Attendre 30s que init.sql s'exécute
docker exec -it skimap-postgis psql -U postgres -d skimap -c "SELECT COUNT(*) FROM stations;"
```

---

## 🔧 Configuration

### settings.py (Principaux paramètres)

```python
# Base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('DB_NAME', 'skimap'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Frontend Vite
]

# Apps installées
INSTALLED_APPS = [
    ...
    'django.contrib.gis',
    'rest_framework',
    'corsheaders',
    'stations',
    'lidar_processing',  # Module LIDAR
]
```

---

## 📞 Support

1. Tester les endpoints : `curl http://localhost:8000/health/`

---

**🎿 Backend SkiMap - Prêt pour l'action ! ⛷️**
