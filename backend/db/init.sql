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

-- seed minimal
INSERT INTO stations (nom, geom) VALUES
('Station Démo', ST_GeomFromText('POINT(6.869 45.923)', 4326));

INSERT INTO pistes (station_id, nom, geom) VALUES
(1, 'Piste Démo', ST_GeomFromText('LINESTRING(6.869 45.923, 6.872 45.925)', 4326));