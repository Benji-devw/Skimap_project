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
  date_time: string;
  temperature_c: number | null;
  precipitation_mm: number | null;
  total_snow_height_cm: number | null;
  natural_snow_height_cm: number | null;
  artificial_snow_height_cm: number | null;
  artificial_snow_production_m3: number | null;
  station_id: number;
  station_nom: string;
  station: Station;
};

export type WeatherData = {
  station_id: number;
  station_nom: string;
  latitude: number;
  longitude: number;
  fetched_at: string;
  snow_depth_cm: number | null;
  snowfall_cm: number | null;
  temperature_c: number | null;
  precipitation_mm: number | null;
  source: "open-meteo";
};
