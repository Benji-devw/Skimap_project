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

| Ressource     | Méthode | URL                      | Description                      |
| ------------- | ------- | ------------------------ | -------------------------------- |
| Stations      | GET     | /api/stations/           | Liste toutes les stations        |
| Stations      | POST    | /api/stations/           | Créer une nouvelle station       |
| Stations      | GET     | /api/stations/{id}/      | Récupérer une station spécifique |
| Stations      | PUT     | /api/stations/{id}/      | Mettre à jour une station        |
| Stations      | DELETE  | /api/stations/{id}/      | Supprimer une station            |
| Pistes        | GET     | /api/pistes/             | Liste toutes les pistes          |
| Pistes        | POST    | /api/pistes/             | Créer une nouvelle piste         |
| Pistes        | GET     | /api/pistes/{id}/        | Récupérer une piste spécifique   |
| Pistes        | PUT     | /api/pistes/{id}/        | Mettre à jour une piste          |
| Pistes        | DELETE  | /api/pistes/{id}/        | Supprimer une piste              |
| Snow measures | GET     | /api/snow_measures/      | Liste toutes les mesures neige   |
| Snow measures | POST    | /api/snow_measures/      | Créer une mesure neige           |
| Snow measures | GET     | /api/snow_measures/{id}/ | Récupérer une mesure spécifique  |
| Snow measures | PUT     | /api/snow_measures/{id}/ | Mettre à jour une mesure         |
| Snow measures | DELETE  | /api/snow_measures/{id}/ | Supprimer une mesure             |

### ⚡ Endpoints personnalisés

| Endpoint      | Exemple d’appel                     | Description|
| --------------                    | ------------------------------------| --------------------------------|
| /api/pistes/{id}/                 | /api/pistes/1/                                         | Infos + géométrie d’une piste précise  |
| /api/stations/{id}/snow_measures  | /api/stations/1/snow_measures?limit=50                 | Mesures neige d’une station (GET/POST) |

## Etape 4 - Update data

```powershell
> docker compose down -v && docker compose up -d
or
> docker exec -it skimap-postgis psql -U postgres -d skimap
> TRUNCATE pistes, stations RESTART IDENTITY CASCADE;
> \i /docker-entrypoint-initdb.d/init.sql
```