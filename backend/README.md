# Backend Steps

## Étape 1 – Créer l’app Django pour l’API

```powershell
> cd ..\SkiMap_Project\backend\django
> python manage.py startapp stations
```

## Étape 2 – Migration

```powershell
> docker compose exec web python manage.py makemigrations
> docker compose exec web python manage.py migrate
> docker compose exec web python manage.py runserver 0.0.0.0:8000
```

## Étape 3 – Vérifier l’API

```powershell
> curl http://localhost:8000/api/stations/
> curl http://localhost:8000/api/pistes/
```

### 🌍 API publique (préfixe /api/)

| Ressource | Méthode | URL                 | Description                      |
| --------- | ------- | ------------------- | -------------------------------- |
| Stations  | GET     | /api/stations/      | Liste toutes les stations        |
| Stations  | POST    | /api/stations/      | Créer une nouvelle station       |
| Stations  | GET     | /api/stations/{id}/ | Récupérer une station spécifique |
| Stations  | PUT     | /api/stations/{id}/ | Mettre à jour une station        |
| Stations  | DELETE  | /api/stations/{id}/ | Supprimer une station            |
| Pistes    | GET     | /api/pistes/        | Liste toutes les pistes          |
| Pistes    | POST    | /api/pistes/        | Créer une nouvelle piste         |
| Pistes    | GET     | /api/pistes/{id}/   | Récupérer une piste spécifique   |
| Pistes    | PUT     | /api/pistes/{id}/   | Mettre à jour une piste          |
| Pistes    | DELETE  | /api/pistes/{id}/   | Supprimer une piste              |

### ⚡ Endpoints personnalisés

| Endpoint               | Exemple d’appel                                        | Description                           |
| ---------------------- | ------------------------------------------------------ | ------------------------------------- |
| /api/stations/proches/ | /api/stations/proches/?lat=45.923&lng=6.869&rayon=5000 | Stations proches d’un point donné     |
| /api/pistes/{id}/      | /api/pistes/1/                                         | Infos + géométrie d’une piste précise |


## Etape 4 - Update data
```powershell
> docker compose down -v && docker compose up -d
or
> docker exec -it skimap-postgis psql -U postgres -d skimap
> TRUNCATE pistes, stations RESTART IDENTITY CASCADE;
> \i /docker-entrypoint-initdb.d/init.sql
```

# TODO

- [x] Init Projet Django + DRF + PostGIS (GeoDjango) configuré
- [x] CORS activé pour le front (Vite)
- [x] Modèles `Station` (Point) et `Piste` (LineString) mappés aux tables existantes
- [x] Serializers exposant GeoJSON et longitude/latitude pour `Station`
- [x] ViewSets REST: `StationViewSet`, `PisteViewSet` avec filtres (`station_id`, recherche spatiale via `lat`/`lng`/`rayon`)
- [x] Routes DRF sous préfixe `/api/` via `DefaultRouter`
- [x] Script `init.sql` (création tables, index GIST, colonnes additionnelles, seed de données)
- [x] Ajoute un modèle pour les mesures météo/neige :
température, précipitations, hauteur de neige, production de neige artificielle.
- [x] Crée un endpoint d’API REST :
GET /stations/{id}/snow → retourne les mesures/production pour cette station.
POST /stations/{id}/snow → permet d’insérer de nouvelles mesures (même simulées).
- [ ] Endpoint dédié ou doc claire pour stations proches (ex: `/api/stations/proches/`) au lieu de seulement des query params
- [ ] Pagination, tri, et filtres supplémentaires (nom, type, état) sur les listes
- [ ] Endpoint GeoJSON FeatureCollection pour `pistes` et `stations` (export direct)
- [ ] Tests unitaires (serializers, filtres spatiaux, endpoints) dans `stations/tests.py`
- [ ] Admin Django: enregistrement `Station`/`Piste` avec aperçus géométriques
- [ ] Documentation OpenAPI (Swagger) avec `drf-spectacular` ou `drf-yasg`
- [ ] Commande de management pour importer des pistes/stations depuis GeoJSON/GPX
- [ ] Sécurisation basique (throttling, permissions si nécessaire) et limites de taille de réponse
