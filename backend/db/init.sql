-- connectez-vous: psql -h localhost -U postgres -d skimap
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE stations (
  id SERIAL PRIMARY KEY,
  nom TEXT NOT NULL,
  geom geometry(POINT, 4326) NOT NULL
);

CREATE TABLE pistes (
  id SERIAL PRIMARY KEY,
  station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
  nom TEXT NOT NULL,
  geom geometry(LINESTRING, 4326) NOT NULL
);

CREATE INDEX idx_pistes_geom ON pistes USING GIST (geom);

-- Colonnes additionnelles pour enrichir les pistes
ALTER TABLE pistes ADD COLUMN IF NOT EXISTS type TEXT;
ALTER TABLE pistes ADD COLUMN IF NOT EXISTS etat TEXT;
ALTER TABLE pistes ADD COLUMN IF NOT EXISTS longueur INTEGER;

-- Mesures météo/neige par station
CREATE TABLE IF NOT EXISTS snow_measures (
  id SERIAL PRIMARY KEY,
  station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
  date_time TIMESTAMP NOT NULL,
  temperature_c NUMERIC(5,2),
  precipitation_mm NUMERIC(6,2),
  total_snow_height_cm NUMERIC(6,2),
  natural_snow_height_cm NUMERIC(6,2),
  artificial_snow_height_cm NUMERIC(6,2),
  artificial_snow_production_m3 NUMERIC(10,2)
);

CREATE INDEX IF NOT EXISTS idx_snow_measures_station ON snow_measures(station_id);
CREATE INDEX IF NOT EXISTS idx_snow_measures_date ON snow_measures(date_time);

-- Seed: (coordonnées WGS84 = LON, LAT)
-- Station : Alpe d'Huez
INSERT INTO stations (id, nom, geom) VALUES
(1, 'Alpe d''Huez',
  ST_SetSRID(ST_GeomFromGeoJSON('{
    "type":"Point",
    "coordinates":[6.068348,45.092624]
  }'), 4326));

 -- Station : Les Deux Alpes
INSERT INTO stations (id, nom, geom) VALUES
(2, 'Les Deux Alpes',
  ST_SetSRID(ST_GeomFromGeoJSON('{
    "type":"Point",
    "coordinates":[6.125625180539144,45.01028601911859]
  }'), 4326));

-- Pistes principales
INSERT INTO pistes (id, station_id, nom, geom, type, etat, longueur) VALUES
-- Sarenne (noire, la plus longue du monde)
(1, 1, 'Sarenne',
  ST_SetSRID(ST_GeomFromGeoJSON('{
    "type":"LineString",
    "coordinates":[
      [6.12595096706734,45.10721797232468],
      [6.128199881796468,45.096370771813135],
      [6.126325786188863,45.087373969221936],
      [6.133136682443073,45.083831058853924]
    ]
  }'), 4326),
  'black', 'open', 16000),
-- Alpette (rouge)
(2, 1, 'Alpette',
  ST_SetSRID(ST_GeomFromGeoJSON('{
    "type":"LineString",
    "coordinates":[
      [6.093693619277671,45.13981467189747],
      [6.073180386279292,45.129994502369904]
    ]
  }'), 4326),
  'red', 'close', 1200),
-- Vallon du Diable (rouge)
(3, 2, 'Vallon du Diable',
  ST_SetSRID(ST_GeomFromGeoJSON('{
    "type":"LineString",
    "coordinates":[
      [6.148139039034766, 44.997573878012524],
      [6.144061874947561, 45.009154959403894]
    ]
  }'), 4326),
  'red', 'close', 800);

-- Snow measures
INSERT INTO snow_measures (
  station_id,
  date_time,
  temperature_c,
  precipitation_mm,
  total_snow_height_cm,
  natural_snow_height_cm,
  artificial_snow_height_cm,
  artificial_snow_production_m3
) VALUES
  (1, '2025-01-01 08:00:00', -2.5,  5, 20, 15,  5,   0),
  (1, '2025-01-02 08:00:00', -1.0,  0, 22, 17,  5,  50),
  (1, '2025-01-03 08:00:00',  1.2, 10, 18, 14,  4, 200),
  (2, '2025-01-04 08:00:00',  0.0,  2, 17, 12,  5, 100),
  (2, '2025-01-05 08:00:00', -3.0,  0, 25, 18,  7,   0);

 