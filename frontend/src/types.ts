export type LineStringGeometry = {
  type: "LineString";
  coordinates: [number, number][];
};

export type Piste = {
  id: number;
  nom: string;
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
