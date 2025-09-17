# Fontend Steps

## Étape 1 – Create vite app

```powershell
> cd ../SkiMap_Project
> npm create vite@latest frontend -- --template react-ts
```

## Étape 2 – Ajout de Mapbox
```powershell
> npm i mapbox-gl
```

## Étape 3 – Ajout du .env et token
```powershell
VITE_MAPBOX_TOKEN=pk...
VITE_API_URL=http://localhost:8000
```


# TODO

- [x] Initialisation Vite (React + TS)
- [x] Intégration Mapbox GL et configuration des variables d'environnement (`VITE_MAPBOX_TOKEN`, `VITE_API_URL`)
- [x] Composant `MapView` avec carte de base, marqueurs de stations et popup
- [x] Récupération des stations et des pistes via l'API
- [x] Rendu des pistes via `GeoJSON` (`renderPistesLayer`)
- [x] Basculer style carte: rues ↔ satellite, avec ré‑application 3D et pistes
- [x] Mode 3D (terrain DEM + animation) via `enable3D` / `disable3D`
- [x] Zoom sur station (marker click) et sur piste (sélection sidebar)
- [x] Mode 
- [ ] Adoucir le rendu des pistes: `line-join: "round"`, `line-cap: "round"`, `line-blur`
- [ ] Activer `antialias` et régler `fadeDuration` lors de l'init de la map
- [ ] En mode 3D, ajuster le zoom sur piste: `flyTo` avec `offset/padding` et `queryTerrainElevation` pour éviter la caméra sous le relief
- [ ] Optionnel: orienter la caméra selon l'axe de la piste (calcul du `bearing`)
- [ ] Améliorer la gestion des marqueurs: éviter les doublons et nettoyer à l'update
- [ ] États chargement/erreur pour les `fetch` (stations/pistes)
- [ ] Fit bounds sur l'ensemble de la piste plutôt que centrer sur un seul point
- [ ] Mettre à jour la source `pistes` sans la recréer (meilleures perfs)
- [ ] UI Sidebar: afficher altitude/longueur, filtres par type/difficulté/état
- [ ] Responsivité mobile + gestures (padding, safe areas)
- [ ] Persister `is3D`/`isSatellite` dans `localStorage`
- [ ] Typer GeoJSON avec `@types/geojson` et affiner les types `Piste/Station`