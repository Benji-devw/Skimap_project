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

---

# API Steps

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
