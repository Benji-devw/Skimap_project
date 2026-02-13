# ❄️ SkiMap – Visualisation des pistes de ski

### Objectif
Créer une petite appli Full Stack qui :
- Stocke des pistes de ski et des stations dans PostgreSQL + PostGIS
- Expose une API REST (Node.js ou Django)
- Affiche une carte interactive avec React + Mapbox
- Dockerise le tout pour faciliter le lancement
- INPROGRESS : Ajouter des données LIDAR pour les pistes (si temps)
- TODO: Ajouter des données de neige (mesures historiques, prévisions)
- TODO: Ajouter une fonctionnalité de recherche de stations proches d’une position donnée
- TODO: Ajouter une fonctionnalité de filtrage des pistes par niveau (vert, bleu, rouge, noir)


### Concept
Qu'est-ce que LIDAR ?
- LIDAR (Light Detection and Ranging) est une technologie de télédétection qui utilise des lasers pour mesurer des distances. Elle est couramment utilisée pour créer des modèles 3D précis de la surface de la Terre, des bâtiments, des forêts, etc. Les données LIDAR sont généralement stockées dans des formats spécifiques, comme **LAS** ou **LAZ**, qui sont des standards pour les nuages de points.

Structure des données LIDAR
-Les fichiers LIDAR contiennent des nuages de points, où chaque point représente une mesure avec des informations associées, telles que :
- **Coordonnées spatiales** : X, Y, Z (latitude, longitude, altitude).
- **Intensité** : La force du signal laser réfléchi.
- **Classification** : Indique le type d'objet (sol, végétation, bâtiment, etc.).
- **Temps** : Timestamp pour chaque point (utile pour les systèmes dynamiques).
- **Couleur** : Valeurs RGB (si disponible).
- **Retour multiple** : Certains lasers peuvent détecter plusieurs retours pour un seul tir (utile pour analyser la végétation dense).

Formats courants pour les données LIDAR
- **LAS** : Format binaire standard pour les nuages de points LIDAR.
- **LAZ** : Version compressée de LAS.
- **ASCII** : Format texte, moins efficace mais lisible par l'humain.
- **GeoTIFF** : Utilisé pour les modèles de terrain dérivés des données LIDAR.

Nuages de points LiDAR
- **MNT** (modèles numériques de terrain), 
- **MNS** (modèles numériques de surface)
- **MNH** (modèles numériques de hauteur).
- https://geoservices.ign.fr/lidarhd


## Backend
### Base de données (PostgreSQL + PostGIS)
- Table `stations`: `id`, `nom`, `latitude`, `longitude`
- Table `pistes`: `id`, `nom`, `geom` (LINESTRING)

### API (ex. Node.js + Express)
- `GET /stations` → renvoie toutes les stations
- `GET /pistes/:stationId` → renvoie les pistes d’une station
- `GET /stations/proches?lat=...&lng=...&rayon=...` → stations dans un rayon via `ST_DWithin`

## Frontend (React)
- Page principale avec Mapbox
- Afficher toutes les stations avec des markers
- Clic sur une station → charger et afficher les pistes (lignes)
- Sidebar listant les pistes avec bouton pour zoomer sur la piste

## Bonus (si temps)
- Ajouter un Dockerfile pour lancer API + DB
- Auth simple JWT (login fictif)
- Filtrer par niveau de piste (vert, bleu, rouge, noir)

## Démo attendue
- Backend tourne en local avec Postgres/PostGIS
- Frontend montre une carte avec Mapbox + interaction
- API exposée en JSON (preuve de maîtrise full stack)

________________________________________________________

# Docker Steps

## Étape 1 – Lancer la stack (Docker Compose)

```powershell
> cd ../SkiMap_Project
> docker compose up -d --build
```

## Étape 2 – Vérifier les conteneurs

```powershell
> docker compose ps
```

Attendus:

- skimap-postgis (5432:5432)
- skimap-django (8000:8000)

## Étape 3 – Accéder au backend Django

- Premier démarrage: go to backend/django/REAMDE.md

...
- Ouvrir: http://localhost:8000/
- Si "Bad Request (400)", ajouter `ALLOWED_HOSTS = ["*"]` dans `backend/django/skimap_backend/settings.py`, puis:

```powershell
> docker compose restart web
```

### Endpoint de santé

- Tester: http://localhost:8000/health/
- Réponse attendue:

```json
{ "status": "ok" }
```

## Étape 4 – Base de données PostGIS (déjà initialisée)

- Le script `backend/db/init.sql` est exécuté automatiquement au premier démarrage.
- Connexion manuelle si besoin:

```powershell
> docker exec -it skimap-postgis psql -U postgres -d skimap
```

- Vérifications rapides dans `psql`:

```sql
\dt
SELECT COUNT(*) FROM stations;
SELECT COUNT(*) FROM pistes;
```

## Étape 5 – Arrêt / redémarrage

```powershell
> docker compose stop
> docker compose start
> docker compose down
```
