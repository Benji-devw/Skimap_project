
#  Docker Steps

## Étape 1 – Lancer la stack (Docker Compose)
``` powershell
> docker compose up -d --build
```

## Étape 2 – Vérifier les conteneurs
``` powershell
> docker compose ps
```
Attendus:
- skimap-postgis (5432:5432)
- skimap-django (8000:8000)

## Étape 3 – Accéder au backend Django
- Ouvrir: http://localhost:8000/
- Si "Bad Request (400)", ajouter `ALLOWED_HOSTS = ["*"]` dans `backend/django/skimap_backend/settings.py`, puis:
``` powershell
> docker compose restart web
```

### Endpoint de santé
- Tester: http://localhost:8000/health/
- Réponse attendue:
``` json
{"status": "ok"}
```

## Étape 4 – Base de données PostGIS (déjà initialisée)
- Le script `backend/db/init.sql` est exécuté automatiquement au premier démarrage.
- Connexion manuelle si besoin:
``` powershell
> docker exec -it skimap-postgis psql -U postgres -d skimap
```
- Vérifications rapides dans `psql`:
``` sql
\dt
SELECT COUNT(*) FROM stations;
SELECT COUNT(*) FROM pistes;
```

## Étape 5 – Arrêt / redémarrage
``` powershell
> docker compose stop
> docker compose start
> docker compose down
```

## (Optionnel) Basculer Django sur Postgres
- `backend/django/skimap_backend/settings.py`:
``` python
import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "skimap"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}
```

- `docker-compose.yml` (service `web`):
``` yaml
environment:
  DJANGO_DEBUG: "1"
  DB_NAME: skimap
  DB_USER: postgres
  DB_PASSWORD: postgres
  DB_HOST: db
  DB_PORT: "5432"
command: sh -c "until pg_isready -h $$DB_HOST -p $$DB_PORT -U $$DB_USER; do echo '⏳ attente DB...'; sleep 2; done; python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
depends_on:
  db:
    condition: service_healthy
```

#  API Steps

## Étape 1 – Créer l’app Django pour l’API
``` powershell
> cd ..\SkiMap_Project\backend\django
> python manage.py startapp stations
```

