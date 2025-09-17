export type LineStringGeometry = {
  type: "LineString";
  coordinates: [number, number][];
};

export type Piste = {
  id: number;
  nom: string;
  type: string;
  etat: string;
  longueur: number;
  geometry: LineStringGeometry | null;
};

export type PointGeometry = {
  type: "Point";
  coordinates: [number, number];
};

export type Station = {
  id: number;
  nom: string;
  longitude: number;
  latitude: number;
  geometry?: PointGeometry;
};

export type SnowMeasure = {
  id: number;
  date_heure: string;
  temperature_c: number | null;
  precipitations_mm: number | null;
  hauteur_neige_totale_cm: number | null;
  hauteur_neige_naturelle_cm: number | null;
  hauteur_neige_artificielle_cm: number | null;
  production_neige_artificielle_m3: number | null;
  station_id: number;
  station_nom: string;
};