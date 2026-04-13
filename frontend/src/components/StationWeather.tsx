import { useEffect, useState } from "react";
import type { Station, WeatherData } from "../types";

type Props = {
  station: Station;
};

function SnowBar({ value, max = 200 }: { value: number; max?: number }) {
  const pct = Math.min((value / max) * 100, 100);
  const color =
    value < 10
      ? "#ef4444"
      : value < 30
        ? "#f97316"
        : value < 50
          ? "#eab308"
          : value < 80
            ? "#22c55e"
            : value < 120
              ? "#00CCFF"
              : "#ffffff";

  return (
    <div
      style={{
        width: "100%",
        height: 6,
        borderRadius: 3,
        background: "rgba(255,255,255,0.1)",
        marginTop: 4,
      }}
    >
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          borderRadius: 3,
          background: color,
          transition: "width 0.6s ease",
        }}
      />
    </div>
  );
}

function SnowLabel({ cm }: { cm: number | null }) {
  if (cm === null) return <span style={{ opacity: 0.5 }}>N/A</span>;
  if (cm < 10)
    return <span style={{ color: "#ef4444" }}>{cm} cm — Pas de neige</span>;
  if (cm < 30)
    return <span style={{ color: "#f97316" }}>{cm} cm — Très peu</span>;
  if (cm < 50) return <span style={{ color: "#eab308" }}>{cm} cm — Peu</span>;
  if (cm < 80) return <span style={{ color: "#22c55e" }}>{cm} cm — Moyen</span>;
  if (cm < 120) return <span style={{ color: "#00CCFF" }}>{cm} cm — Bon</span>;
  return <span style={{ color: "#ffffff" }}>{cm} cm — Excellent ⭐</span>;
}

export default function StationWeather({ station }: Props) {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!station) return;

    setLoading(true);
    setError(null);
    setWeather(null);

    fetch(
      `${import.meta.env.VITE_API_URL}/api/snow-realtime/?station_id=${station.id}`,
    )
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: WeatherData) => {
        setWeather(data);
      })
      .catch((err) => {
        setError(err.message ?? "Erreur inconnue");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [station]);

  const containerStyle: React.CSSProperties = {
    marginTop: 12,
    padding: "12px 14px",
    borderRadius: 8,
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.1)",
    fontSize: 13,
  };

  const rowStyle: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "5px 0",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  };

  const lastRowStyle: React.CSSProperties = {
    ...rowStyle,
    borderBottom: "none",
  };

  const labelStyle: React.CSSProperties = {
    opacity: 0.65,
    fontSize: 12,
  };

  const valueStyle: React.CSSProperties = {
    fontWeight: 600,
  };

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={{ opacity: 0.5, textAlign: "center", padding: "8px 0" }}>
          ⏳ Chargement météo…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={{ color: "#ff6b6b", fontSize: 12 }}>
          ⚠️ Météo indisponible
        </div>
      </div>
    );
  }

  if (!weather) return null;

  const fetchedAt = new Date(weather.fetched_at).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 13 }}>
          ☁️ Météo en temps réel
        </span>
        <span style={{ fontSize: 11, opacity: 0.45 }}>
          Open-Meteo · {fetchedAt} UTC · {new Date().toLocaleString()}
        </span>
      </div>

      {/* Neige au sol */}
      <div style={{ marginBottom: 10 }}>
        <div style={{ ...rowStyle, borderBottom: "none", paddingBottom: 2 }}>
          <span style={labelStyle}>❄️ Hauteur de neige</span>
          <span style={valueStyle}>
            <SnowLabel cm={weather.snow_depth_cm} />
          </span>
        </div>
        {weather.snow_depth_cm !== null && (
          <SnowBar value={weather.snow_depth_cm} />
        )}
      </div>

      {/* Chute de neige */}
      <div style={rowStyle}>
        <span style={labelStyle}>🌨️ Chute de neige</span>
        <span style={valueStyle}>
          {weather.snowfall_cm !== null ? (
            `${weather.snowfall_cm} cm`
          ) : (
            <span style={{ opacity: 0.5 }}>N/A</span>
          )}
        </span>
      </div>

      {/* Température */}
      <div style={rowStyle}>
        <span style={labelStyle}>🌡️ Température</span>
        <span
          style={{
            ...valueStyle,
            color:
              weather.temperature_c === null
                ? undefined
                : weather.temperature_c <= 0
                  ? "#00CCFF"
                  : weather.temperature_c <= 5
                    ? "#86efac"
                    : "#f97316",
          }}
        >
          {weather.temperature_c !== null ? (
            `${weather.temperature_c} °C`
          ) : (
            <span style={{ opacity: 0.5 }}>N/A</span>
          )}
        </span>
      </div>

      {/* Précipitations */}
      <div style={lastRowStyle}>
        <span style={labelStyle}>💧 Précipitations</span>
        <span style={valueStyle}>
          {weather.precipitation_mm !== null ? (
            `${weather.precipitation_mm} mm`
          ) : (
            <span style={{ opacity: 0.5 }}>N/A</span>
          )}
        </span>
      </div>
    </div>
  );
}
