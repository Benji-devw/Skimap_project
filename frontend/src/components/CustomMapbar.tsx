import '../styles/StyledCustomMapButton.css';

type Props = {
  is3D: boolean;
  setIs3D: (v: boolean) => void;
  isSatellite: boolean;
  setIsSatellite: (v: boolean) => void;
};

export default function CustomMapbar({ is3D, setIs3D, isSatellite, setIsSatellite }: Props) {
  return (
    <div className="custom-mapbar">
      <button className="styled-button" onClick={() => setIs3D(!is3D)}>
        {is3D ? "Vue 2D" : "Vue 3D"}
      </button>
      
      <button className="styled-button" onClick={() => setIsSatellite(!isSatellite)}>
        {isSatellite ? "Satellite: ON" : "Satellite: OFF"}
        <span className="inner-button"><span className="icon">🛰️</span></span>
      </button>
    </div>
  );
}
