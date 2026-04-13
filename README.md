# ❄️ SkiMap – Visualisation des pistes de ski avec couche neige LIDAR

## 📋 Vue d'ensemble

Application Full Stack de visualisation interactive de pistes de ski avec :
- **Carte 3D interactive** (Mapbox GL JS)
- **Couche de neige prédictive** basée sur données LIDAR
- **API REST** Django avec PostGIS
- **Frontend React + TypeScript**
- **Architecture Docker** complète

## ✨ Fonctionnalités

### 🗺️ Carte Interactive
- ✅ Visualisation 3D du terrain avec relief
- ✅ Mode satellite / carte classique
- ✅ Affichage des stations de ski (markers cliquables)
- ✅ Tracé des pistes avec couleurs par difficulté
- ✅ Dessin de nouvelles pistes directement sur la carte
- ✅ Rotation de la carte (bearing) avec réinitialisation

### ❄️ Couche de Neige LIDAR (NOUVEAU !)
- ✅ **Prédiction d'accumulation de neige** basée sur :
  - Modèle Numérique de Terrain (MNT) - altitude
  - Pente (slope) - où la neige glisse ou s'accumule
  - Exposition (aspect) - ensoleillement et fonte
  - Exposition au vent - réduction sur crêtes
- ✅ **Visualisation colorée** : Rouge (pas de neige) → Vert (moyen) → Bleu (bon) → Blanc (excellent)
- ✅ **Popups interactifs** au survol avec détails
- ✅ **Toggle ON/OFF** depuis l'interface
- ✅ **API REST** pour récupérer les données

### 📊 Données
- ✅ Stations de ski avec coordonnées GPS
- ✅ Pistes avec géométrie LineString (GeoJSON)
- ✅ Mesures de neige (température, précipitations, hauteur)
- ✅ Traitement LIDAR (30M+ points) pour analyse terrain


## 📚 Concept
Qu'est-ce que LIDAR ?
- LIDAR (Light Detection and Ranging) est une technologie de télédétection qui utilise des lasers pour mesurer des distances. Elle est couramment utilisée pour créer des modèles 3D précis de la surface de la Terre, des bâtiments, des forêts, etc. Les données LIDAR sont généralement stockées dans des formats spécifiques, comme **LAS** ou **LAZ**, qui sont des standards pour les nuages de points.

### 📚 Formats courants pour les données LIDAR
- **LAS** : Format binaire standard pour les nuages de points LIDAR.
- **LAZ** : Version compressée de LAS.
- **ASCII** : Format texte, moins efficace mais lisible par l'humain.
- **GeoTIFF** : Utilisé pour les modèles de terrain dérivés des données LIDAR.


## 🏗️ Architecture

```
Skimap_project/
├── backend/
│   ├── db/                          # Scripts PostgreSQL
│   │   ├── init.sql                 # Schéma initial + données
│   │   └── fix_sequences.sql        # Fix IDs auto-increment
│   │
│   └── django/                      # API Django
│       ├── stations/                # App principale
│       │   ├── models.py            # Station, Piste, SnowMeasure
│       │   ├── views.py             # API endpoints + LIDAR endpoints
│       │   ├── serializers.py       # Serialization GeoJSON
│       │   └── admin.py             # Interface admin
│       │
│       ├── lidar_processing/        # Module LIDAR (NOUVEAU)
│       │   └── management/commands/ # Django commands
│       │       └── explore_lidar.py # Analyse fichiers LAZ
│       │
│       ├── media/lidar/             # Données LIDAR traitées
│       │   ├── *.laz                # Fichiers LIDAR source (30M points)
│       │   ├── dtm_*.tif            # Modèles Numériques de Terrain
│       │   ├── snow_prediction.tif  # Prédiction neige
│       │   └── snow_contours.geojson # GeoJSON pour Mapbox (5Mo)
│       │
│       ├── analyze_lidar.py         # Script analyse LIDAR
│       ├── create_dtm.py            # Génération MNT + pente + exposition
│       ├── predict_snow_coverage.py # Modèle d'accumulation neige
│       ├── convert_raster_to_geojson.py # Conversion pour web
│       │
│       ├── requirements.txt         # Dépendances Python
│       └── manage.py                # Django CLI
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.tsx         # Carte Mapbox principale
│   │   │   ├── Topbar.tsx          # Barre d'outils supérieure
│   │   │   ├── CustomMapbar.tsx    # Contrôles 3D/Satellite/Neige
│   │   │   ├── Sidebar.tsx         # Liste des pistes
│   │   │   └── PisteDrawer.tsx     # Création de pistes
│   │   │
│   │   ├── utils/
│   │   │   ├── map3D.ts            # Gestion terrain 3D
│   │   │   ├── pistesLayer.ts      # Affichage pistes
│   │   │   └── snowLayer.ts        # Couche neige (NOUVEAU)
│   │   │
│   │   ├── types.ts                # Types TypeScript
│   │   ├── App.tsx                 # Composant racine
│   │   └── main.tsx                # Point d'entrée
│   │
│   ├── package.json                # Dépendances Node.js
│   └── vite.config.ts              # Config Vite
│
├── docker-compose.yml              # Orchestration Docker
├── LIDAR_SNOW_INTEGRATION.md       # Doc complète LIDAR (NOUVEAU)
├── TESTING_GUIDE.md                # Guide de test (NOUVEAU)
└── README.md                       # Ce fichier
```

---

## 🚀 Installation et Démarrage

### Prérequis

- **Docker** + Docker Compose
- **Node.js** 18+ (pour le frontend)
- **Token Mapbox** (gratuit sur https://mapbox.com)

### 1. Cloner le projet

```bash
git clone <votre-repo>
cd Skimap_project
```

### 2. Configuration

Créer le fichier `.env` dans `frontend/` :

```env
VITE_MAPBOX_TOKEN=pk.votre_token_mapbox
VITE_API_URL=http://localhost:8000
```

### 3. Lancer le backend (Docker)

```bash
# Démarrer PostgreSQL + Django
docker compose up -d --build

# Vérifier que les conteneurs tournent
docker compose ps
```

**Services disponibles :**
- API Django : http://localhost:8000
- PostgreSQL PostGIS : localhost:5432
- Health check : http://localhost:8000/health/

### 4. Lancer le frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

**Application disponible :** http://localhost:5173

---

## 📡 API Endpoints

### Endpoints Principaux

| Méthode | URL | Description |F
|---------|-----|-------------|
| `GET` | `/api/stations/` | Liste toutes les stations |
| `POST` | `/api/stations/` | Créer une station |
| `GET` | `/api/stations/{id}/` | Détails d'une station |
| `GET` | `/api/pistes/` | Liste toutes les pistes |
| `GET` | `/api/pistes/?station_id={id}` | Pistes d'une station |
| `POST` | `/api/pistes/` | Créer une piste |
| `GET` | `/api/snow_measures/` | Mesures de neige |
| `POST` | `/api/snow_measures/` | Ajouter une mesure |

### Endpoints LIDAR Neige (NOUVEAU) ❄️

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/snow-coverage/` | GeoJSON complet de la couche neige |
| `GET` | `/api/snow-at-point/?lat=X&lng=Y` | Hauteur de neige à un point |

**Exemple de réponse `/api/snow-at-point/` :**
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

## 🎨 Utilisation

### Interface Utilisateur

1. **Afficher les stations** : Les markers apparaissent automatiquement
2. **Voir les pistes** : Cliquer sur un marker de station
3. **Zoom sur une piste** : Cliquer sur une piste dans la sidebar
4. **Activer la 3D** : Bouton "Vue 3D"
5. **Mode satellite** : Bouton "Satellite: OFF/ON"
6. **Couche de neige** : Bouton "Neige: OFF/ON" ❄️
7. **Créer une piste** : Bouton "+" puis cliquer sur la carte
8. **Réinitialiser orientation** : Bouton "Nord ↑"

### Palette de Couleurs Neige

| Catégorie | Hauteur | Couleur | Code |
|-----------|---------|---------|------|
| Pas de neige | 0-10 cm | 🔴 Rouge | `#FF0000` |
| Très peu | 10-30 cm | 🟠 Orange | `#FF6600` |
| Peu | 30-50 cm | 🟡 Jaune | `#FFCC00` |
| Moyen | 50-80 cm | 🟢 Vert | `#66FF66` |
| Bon | 80-120 cm | 🔵 Bleu | `#00CCFF` |
| Excellent | >120 cm | ⚪ Blanc | `#FFFFFF` |

---

## 🔬 Traitement LIDAR

### Pipeline Complet

```bash
# Depuis le conteneur Django
docker exec -it skimap-django bash

# 1. Analyser un fichier LIDAR
python analyze_lidar.py media/lidar/fichier.laz

# 2. Créer le MNT + pente + exposition
python create_dtm.py \
  --input media/lidar/fichier.laz \
  --output media/lidar/dtm.tif \
  --resolution 2.0 \
  --calculate-slope \
  --calculate-aspect

# 3. Prédire l'accumulation de neige
# Avec données réelles Open-Meteo (recommandé)
python predict_snow_coverage.py \
  --dtm media/lidar/dtm.tif \
  --slope media/lidar/dtm_slope.tif \
  --aspect media/lidar/dtm_aspect.tif \
  --output media/lidar/snow_prediction.tif \
  --lat 44.602 --lon 6.220 \
  --base-elevation 1600 \
  --save-classified

# Ou avec une valeur manuelle (sans connexion)
python predict_snow_coverage.py \
  --dtm media/lidar/dtm.tif \
  --slope media/lidar/dtm_slope.tif \
  --aspect media/lidar/dtm_aspect.tif \
  --output media/lidar/snow_prediction.tif \
  --base-snow 75 \
  --base-elevation 1600 \
  --save-classified

# 4. Convertir en GeoJSON pour Mapbox
python convert_raster_to_geojson.py \
  --input media/lidar/snow_prediction_classified.tif \
  --output media/lidar/snow_contours.geojson \
  --simplify 10
```

### Modèle d'Accumulation

```
neige_prédite = neige_base × 
                facteur_altitude × 
                facteur_pente × 
                facteur_exposition × 
                facteur_vent

Où :
- facteur_altitude  : +10% par 100m d'altitude
- facteur_pente     : Réduction si > 35° (neige glisse)
- facteur_exposition: 0.7 (sud) → 1.2 (nord)
- facteur_vent      : 0.6 sur crêtes exposées
```

---

## 🗄️ Base de Données

### Schéma PostGIS

```sql
-- Table stations
CREATE TABLE stations (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    geom GEOMETRY(Point, 4326)
);

-- Table pistes
CREATE TABLE pistes (
    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES stations(id),
    nom VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    etat VARCHAR(50),
    longueur INTEGER,
    geom GEOMETRY(LineString, 4326)
);

-- Table snow_measures
CREATE TABLE snow_measures (
    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES stations(id),
    date_time TIMESTAMP NOT NULL,
    temperature_c DECIMAL(5,2),
    precipitation_mm DECIMAL(6,2),
    total_snow_height_cm DECIMAL(6,2),
    natural_snow_height_cm DECIMAL(6,2),
    artificial_snow_height_cm DECIMAL(6,2),
    artificial_snow_production_m3 DECIMAL(10,2)
);
```

---

## 🧪 Tests

```bash
# Tester l'API
curl http://localhost:8000/api/stations/ | jq
curl http://localhost:8000/api/snow-coverage/ | jq '.features | length'

# Tester un point spécifique
curl "http://localhost:8000/api/snow-at-point/?lat=44.602&lng=6.220" | jq
```

**Voir aussi :**
- `TESTING_GUIDE.md` - Guide complet de test
- `LIDAR_SNOW_INTEGRATION.md` - Documentation technique LIDAR

---

## 📦 Dépendances

### Backend (Python)

```bash
# Check dependencies
docker compose exec web pip list
```

```txt
django==5.2.6
djangorestframework
django-cors-headers
psycopg2-binary

# Traitement LIDAR
laspy==2.7.0
numpy==2.4.2
scipy==1.17.0
rasterio==1.4.4
shapely==2.1.2
pyproj==3.7.2
```

### Frontend (Node.js)

```json
{
  "mapbox-gl": "^3.15.0",
  "react": "^19.1.1",
  "react-dom": "^19.1.1"
}
```

---

## 🐛 Dépannage

### Problème : API ne répond pas

```bash
# Vérifier les logs
docker compose logs web

# Redémarrer le conteneur
docker compose restart web
```

### Problème : Base de données vide

```bash
# Réinitialiser la DB
docker compose down -v
docker compose up -d

# Attendre 30s que init.sql s'exécute
```

### Problème : Couche de neige ne s'affiche pas

```bash
# Vérifier que le GeoJSON existe
docker exec skimap-django ls -lh media/lidar/snow_contours.geojson

# Si absent, régénérer
docker exec skimap-django python convert_raster_to_geojson.py \
  --input media/lidar/snow_prediction_classified.tif \
  --output media/lidar/snow_contours.geojson
```

### Problème : Transition 3D/Satellite saccadée

- Vérification : Console navigateur (F12) pour erreurs
- Solution : Recharger la page (Ctrl+R)
- Voir : `STYLE_TRANSITION_FIX.md` pour détails

---

## 📈 Performance

| Métrique | Valeur |
|----------|--------|
| Points LIDAR traités | 30,759,941 |
| Zone couverte | 1 km² |
| Résolution MNT | 2 m/pixel |
| Taille GeoJSON neige | 5 Mo |
| Temps traitement LIDAR | ~3 min |
| Temps affichage carte | <1s |

---

## 🔮 Améliorations Futures

### Court terme
- [ ] Ajout d'un timer pour le upload du fichier LAZ
- [ ] Slider d'opacité pour la couche neige
- [ ] Légende des couleurs dans l'UI
- [ ] Sélecteur de date pour données historiques
- [ ] Export des pistes en GPX

### Moyen terme
- [ ] Traiter plusieurs zones LIDAR
- [ ] Modèle prédictif temps réel (API météo)
- [ ] Tuiles vectorielles optimisées (PMTiles)
- [ ] Analyse d'enneigement par piste

### Long terme
- [ ] Machine Learning pour prédiction neige
- [ ] Validation terrain avec mesures réelles
- [ ] API publique de prédiction
- [ ] Application mobile avec AR

---

## 📚 Documentation Complète

- **`LIDAR_SNOW_INTEGRATION.md`** - Documentation technique LIDAR complète
- **`TESTING_GUIDE.md`** - Guide de test détaillé
- **`POPUP_FIX_SUMMARY.md`** - Fix des popups dupliqués
- **`STYLE_TRANSITION_FIX.md`** - Fix transition 3D/Satellite
- **`backend/README.md`** - Documentation backend Django

---

## 🤝 Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📄 Licence

Données LIDAR : IGN France (Licence Ouverte Etalab)  
Code : MIT License

---

## 🙏 Remerciements

- **IGN France** - Données LiDAR HD gratuites
- **Mapbox** - API cartographique
- **PostGIS** - Extension spatiale PostgreSQL
- **Django REST Framework** - API backend

---

## 📞 Contact

**Auteur** : NavArt  
**Date** : Janvier 2025  
**Projet** : SkiMap - Visualisation interactive des pistes de ski  

---

**🎿❄️ Bonne glisse sur SkiMap ! ⛷️🏔️**
