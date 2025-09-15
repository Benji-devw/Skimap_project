# ❄️ SkiMap – Visualisation des pistes de ski

## Objectif
Créer une petite appli Full Stack qui :
- Stocke des pistes de ski et des stations dans PostgreSQL + PostGIS
- Expose une API REST (Node.js ou Django)
- Affiche une carte interactive avec React + Mapbox

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
