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

-- Seed: Alpe d'Huez (coordonnées WGS84 = LON, LAT)
INSERT INTO stations (id, nom, geom) VALUES
(1, 'Alpe d''Huez', ST_SetSRID(ST_GeomFromGeoJSON('{"type":"Point","coordinates":[6.068348,45.092624]}'), 4326));

INSERT INTO pistes (id, station_id, nom, geom, type, etat, longueur) VALUES
(1, 1, 'Sarenne',
  ST_SetSRID(ST_GeomFromGeoJSON('{"type":"LineString","coordinates":[
    [6.12595096706734,45.10721797232468],
    [6.1281998817964680,45.096370771813135],
    [6.126325786188863,45.087373969221936],
    [6.133136682443073,45.083831058853924]
  ]}'), 4326),
  'noire', 'ouverte', 16000
),
(2, 1, 'Alpette',
  ST_SetSRID(ST_GeomFromGeoJSON('{"type":"LineString","coordinates":[
    [ 6.093693619277671,45.13981467189747],
    [6.073180386279292, 45.129994502369904]
  ]}'), 4326),
  'rouge', 'ouverte', 1200
);