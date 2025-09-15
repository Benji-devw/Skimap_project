FROM python:3.11-slim

# Dépendances système (PostGIS client + psycopg2)
RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Créer un dossier app
WORKDIR /app

# Installer Django et dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
