# 🚀 SkiMap - Guide de Démarrage Rapide

## ⚡ Lancement en 5 minutes

### 1. Prérequis
- ✅ Docker Desktop installé et démarré
- ✅ Node.js 18+ installé
- ✅ Token Mapbox (gratuit sur https://mapbox.com)

### 2. Clone et Configuration

\`\`\`bash
# Cloner le projet
git clone <votre-repo>
cd Skimap_project

# Créer le fichier .env frontend
echo "VITE_MAPBOX_TOKEN=pk.votre_token_mapbox" > frontend/.env
echo "VITE_API_URL=http://localhost:8000" >> frontend/.env
\`\`\`

### 3. Démarrer le Backend

\`\`\`bash
# Lancer PostgreSQL + Django
docker compose up -d --build

# Attendre 30s que la DB s'initialise
sleep 30

# Vérifier
curl http://localhost:8000/health/
# → {"status": "ok"}
\`\`\`

### 4. Démarrer le Frontend

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

**✅ Ouvrir** : http://localhost:5173

---

## 🎮 Utilisation

### Carte de Base
1. **Voir les stations** : Markers automatiques
2. **Cliquer sur une station** : Affiche ses pistes
3. **Cliquer sur une piste** (sidebar) : Zoom dessus

### Contrôles
- **Vue 3D** : Active le terrain 3D
- **Satellite** : Change le style de carte
- **Neige ❄️** : Affiche la couche de neige LIDAR
- **Nord ↑** : Réoriente la carte

### Couche de Neige
- 🔴 Rouge : Pas de neige (0-10 cm)
- 🟠 Orange : Très peu (10-30 cm)
- 🟡 Jaune : Peu (30-50 cm)
- 🟢 Vert : Moyen (50-80 cm)
- 🔵 Bleu : Bon (80-120 cm)
- ⚪ Blanc : Excellent (>120 cm)

---

## 📡 API Rapide

\`\`\`bash
# Toutes les stations
curl http://localhost:8000/api/stations/ | jq

# Pistes d'une station
curl "http://localhost:8000/api/pistes/?station_id=1" | jq

# Couche de neige
curl http://localhost:8000/api/snow-coverage/ | jq

# Neige à un point
curl "http://localhost:8000/api/snow-at-point/?lat=44.602&lng=6.220" | jq
\`\`\`

---

## 🔬 Traitement LIDAR (Optionnel)

Si vous avez un fichier LIDAR (.laz) :

\`\`\`bash
# Entrer dans le conteneur
docker exec -it skimap-django bash

# Analyser le fichier
python analyze_lidar.py media/lidar/votre_fichier.laz

# Créer le MNT
python create_dtm.py \\
  --input media/lidar/votre_fichier.laz \\
  --output media/lidar/dtm.tif \\
  --resolution 2.0 \\
  --calculate-slope \\
  --calculate-aspect

# Prédire la neige
python predict_snow_coverage.py \\
  --dtm media/lidar/dtm.tif \\
  --slope media/lidar/dtm_slope.tif \\
  --aspect media/lidar/dtm_aspect.tif \\
  --output media/lidar/snow_prediction.tif \\
  --base-snow 75 \\
  --save-classified

# Convertir en GeoJSON
python convert_raster_to_geojson.py \\
  --input media/lidar/snow_prediction_classified.tif \\
  --output media/lidar/snow_contours.geojson

# Redémarrer pour recharger
docker compose restart web
\`\`\`

---

## 🐛 Problèmes Courants

### Port déjà utilisé
\`\`\`bash
# Arrêter les services
docker compose down
# Vérifier les ports
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
\`\`\`

### Base de données vide
\`\`\`bash
docker compose down -v && docker compose up -d
\`\`\`

### Couche neige invisible
\`\`\`bash
# Vérifier le fichier existe
docker exec skimap-django ls -lh media/lidar/snow_contours.geojson
\`\`\`

---

## 📚 Documentation Complète

- **README.md** : Documentation projet complète
- **LIDAR_SNOW_INTEGRATION.md** : Intégration LIDAR détaillée
- **backend/README.md** : Documentation API
- **TESTING_GUIDE.md** : Guide de test
- **CHANGELOG.md** : Historique des versions

---

## ✅ Checklist Validation

- [ ] Backend répond à http://localhost:8000/health/
- [ ] Frontend accessible sur http://localhost:5173
- [ ] Markers stations visibles sur la carte
- [ ] Clic sur station → pistes s'affichent
- [ ] Bouton "Vue 3D" → terrain 3D activé
- [ ] Bouton "Neige" → zones colorées apparaissent
- [ ] Popup au survol de la couche neige

---

**🎉 Prêt à skier ! 🎿❄️**
