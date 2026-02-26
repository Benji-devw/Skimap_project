# Utilisation d'une image optimisée pour les paquets scientifiques
FROM condaforge/mambaforge:latest

# Installation des outils système et SIG via Mamba
# On installe tout d'un coup : Django, GDAL, PDAL, et les libs Python
RUN mamba install -y -c conda-forge \
    python=3.11 \
    django \
    djangorestframework \
    psycopg2 \
    django-cors-headers \
    gdal \
    pdal \
    python-pdal \
    laspy \
    rasterio \
    numpy \
    scipy \
    && mamba clean -afy

# Créer le dossier app
WORKDIR /app

# Copier le reste du code
COPY . .

# On expose le port 8000
EXPOSE 8000

# Commande de lancement
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
