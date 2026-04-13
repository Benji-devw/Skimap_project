import { useEffect, useRef, useState } from "react";
import type { Station } from "../types";

type PipelineStatus = "none" | "pending" | "running" | "done" | "error";

type UploadEntry = {
  id: number;
  original_filename: string;
  uploaded_at: string | null;
  file_size_mb: number | null;
  file_exists: boolean;
};

type StatusResponse = {
  station_id: number;
  station_nom: string;
  status: PipelineStatus;
  progress_step: string;
  error_message: string;
  snow_layer_ready: boolean;
  laz_count: number;
  dtm: {
    status: string;
    laz_count: number;
    completed_at: string | null;
    ready: boolean;
  };
};

type Props = {
  station: Station;
  onSnowLayerReady: () => void;
  onSnowLayerRemoved?: () => void;
};

const STEP_LABELS: Record<string, string> = {
  "Démarrage du pipeline…": "Démarrage…",
  "Démarrage du pipeline neige…": "Démarrage…",
  "Génération du modèle numérique de terrain (DTM)…": "1/3 — Génération DTM…",
  "Récupération de la hauteur de neige (Open-Meteo)…": "2/3 — Données météo…",
  "Conversion en GeoJSON pour la carte…": "3/3 — Génération carte…",
  "En attente de retraitement…": "En attente…",
};

function normalizeStep(step: string): string {
  for (const [key, label] of Object.entries(STEP_LABELS)) {
    if (step.includes(key)) return label;
  }
  if (step.startsWith("Prédiction")) return "2/3 — Prédiction neige…";
  if (step.startsWith("Fusion")) return "Fusion des zones…";
  return step;
}

function formatSize(mb: number | null): string {
  if (mb === null) return "? Mo";
  if (mb >= 1000) return `${(mb / 1024).toFixed(1)} Go`;
  return `${mb.toFixed(1)} Mo`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function LidarUploader({
  station,
  onSnowLayerReady,
  onSnowLayerRemoved,
}: Props) {
  const [uploads, setUploads] = useState<UploadEntry[]>([]);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("none");
  const [progressStep, setProgressStep] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [snowReady, setSnowReady] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // id du LAZ en cours de suppression
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [cancelling, setCancelling] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const notifiedReadyRef = useRef(false);
  const notifiedRemovedRef = useRef(false);

  // ── Helpers fetch ────────────────────────────────────────────────────

  const fetchStatus = async (): Promise<StatusResponse | null> => {
    try {
      const r = await fetch(
        `${import.meta.env.VITE_API_URL}/api/lidar/status/?station_id=${station.id}`,
      );
      if (!r.ok) return null;
      return await r.json();
    } catch {
      return null;
    }
  };

  const fetchUploads = async (): Promise<UploadEntry[]> => {
    try {
      const r = await fetch(
        `${import.meta.env.VITE_API_URL}/api/lidar/uploads/?station_id=${station.id}`,
      );
      if (!r.ok) return [];
      const data = await r.json();
      return data.uploads ?? [];
    } catch {
      return [];
    }
  };

  // ── Polling ──────────────────────────────────────────────────────────

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const applyStatus = (data: StatusResponse) => {
    setPipelineStatus(data.status);
    setProgressStep(data.progress_step ?? "");
    setErrorMessage(data.error_message ?? "");
    setSnowReady(data.snow_layer_ready === true);

    // Notifier App quand la couche devient prête
    if (data.snow_layer_ready && !notifiedReadyRef.current) {
      notifiedReadyRef.current = true;
      notifiedRemovedRef.current = false;
      onSnowLayerReady();
    }

    // Notifier App quand la couche n'est plus disponible
    if (
      !data.snow_layer_ready &&
      !notifiedRemovedRef.current &&
      notifiedReadyRef.current
    ) {
      notifiedRemovedRef.current = true;
      notifiedReadyRef.current = false;
      onSnowLayerRemoved?.();
    }
  };

  const pollOnce = async () => {
    const [data, list] = await Promise.all([fetchStatus(), fetchUploads()]);
    if (data) applyStatus(data);
    setUploads(list);

    // Arrêter le polling quand le pipeline est terminé ou en erreur
    if (data && data.status !== "pending" && data.status !== "running") {
      stopPolling();
    }
  };

  const startPolling = () => {
    stopPolling();
    pollingRef.current = setInterval(pollOnce, 2500);
  };

  // Chargement initial
  useEffect(() => {
    notifiedReadyRef.current = false;
    notifiedRemovedRef.current = false;
    setDeleteError(null);
    setUploadError(null);

    const init = async () => {
      const [data, list] = await Promise.all([fetchStatus(), fetchUploads()]);
      if (data) {
        applyStatus(data);
        if (data.status === "pending" || data.status === "running") {
          startPolling();
        }
      }
      setUploads(list);
    };

    init();
    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [station.id]);

  // ── Upload ───────────────────────────────────────────────────────────

  const handleUpload = async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "laz" && ext !== "las") {
      setUploadError("Format invalide. Utilisez un fichier .laz ou .las");
      return;
    }

    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("station_id", String(station.id));
    formData.append("laz_file", file);

    try {
      const r = await fetch(
        `${import.meta.env.VITE_API_URL}/api/lidar/upload/`,
        { method: "POST", body: formData },
      );
      const data = await r.json();

      if (!r.ok) {
        setUploadError(data.message ?? `Erreur ${r.status}`);
        return;
      }

      // Rafraîchir la liste et démarrer le polling
      const [statusData, list] = await Promise.all([
        fetchStatus(),
        fetchUploads(),
      ]);
      if (statusData) applyStatus(statusData);
      setUploads(list);
      startPolling();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Erreur réseau");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  // ── Suppression d'un LAZ ─────────────────────────────────────────────

  const handleDeleteUpload = async (uploadId: number, filename: string) => {
    if (
      !window.confirm(
        `Supprimer la zone "${filename}" ?\n\n` +
          (uploads.length > 1
            ? `Les ${uploads.length - 1} autre(s) zone(s) seront conservées et le DTM sera recalculé.`
            : "C'est le dernier fichier LAZ — toutes les données LIDAR seront supprimées."),
      )
    ) {
      return;
    }

    setDeletingId(uploadId);
    setDeleteError(null);
    stopPolling();

    try {
      const r = await fetch(
        `${import.meta.env.VITE_API_URL}/api/lidar/uploads/${uploadId}/`,
        { method: "DELETE" },
      );
      const data = await r.json();

      if (!r.ok) {
        setDeleteError(data.message ?? `Erreur ${r.status}`);
        return;
      }

      // Rafraîchir l'état
      const [statusData, list] = await Promise.all([
        fetchStatus(),
        fetchUploads(),
      ]);
      if (statusData) applyStatus(statusData);
      else {
        // Plus rien pour cette station
        setPipelineStatus("none");
        setProgressStep("");
        setErrorMessage("");
        setSnowReady(false);
        notifiedRemovedRef.current = true;
        notifiedReadyRef.current = false;
        onSnowLayerRemoved?.();
      }
      setUploads(list);

      // Si un pipeline a redémarré, relancer le polling
      if (data.pipeline_restarted) {
        startPolling();
      }
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Erreur réseau");
    } finally {
      setDeletingId(null);
    }
  };

  // ── Annulation pipeline ──────────────────────────────────────────────

  const handleCancel = async () => {
    if (cancelling) return;
    setCancelling(true);
    stopPolling();
    try {
      const r = await fetch(
        `${import.meta.env.VITE_API_URL}/api/lidar/cancel/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ station_id: station.id }),
        },
      );
      if (r.ok) {
        setPipelineStatus("error");
        setProgressStep("Annulé par l'utilisateur");
      }
    } catch {
      // silencieux
    } finally {
      setCancelling(false);
    }
  };

  // ── Dérivés ──────────────────────────────────────────────────────────

  const isProcessing =
    pipelineStatus === "pending" || pipelineStatus === "running";
  const canUpload = !uploading && !isProcessing && deletingId === null;
  const canCancel = isProcessing && !cancelling;

  // ── Styles ───────────────────────────────────────────────────────────

  const labelStyle: React.CSSProperties = {
    opacity: 0.55,
    fontSize: 11,
    marginBottom: 6,
    display: "block",
  };

  const dropzoneStyle: React.CSSProperties = {
    border: `2px dashed ${dragOver ? "#00CCFF" : "rgba(255,255,255,0.2)"}`,
    borderRadius: 8,
    padding: "12px 10px",
    textAlign: "center",
    cursor: canUpload ? "pointer" : "not-allowed",
    transition: "border-color 0.2s, background 0.2s",
    background: dragOver ? "rgba(0,204,255,0.07)" : "rgba(255,255,255,0.04)",
  };

  // ── Rendu de la barre de progression ─────────────────────────────────

  const renderPipelineBar = () => {
    if (pipelineStatus === "none") return null;
    const isDone = pipelineStatus === "done";
    const isError = pipelineStatus === "error";
    const isActive =
      pipelineStatus === "pending" || pipelineStatus === "running";

    const barColor = isDone ? "#22c55e" : isError ? "#ef4444" : "#00CCFF";
    const stepLabel = progressStep
      ? normalizeStep(progressStep)
      : isDone
        ? "Carte de neige prête ✅"
        : isError
          ? "Erreur"
          : "En attente…";

    return (
      <div
        style={{
          marginTop: 8,
          padding: "9px 11px",
          borderRadius: 8,
          background: isDone
            ? "rgba(34,197,94,0.08)"
            : isError
              ? "rgba(239,68,68,0.08)"
              : "rgba(0,204,255,0.07)",
          border: `1px solid ${isDone ? "rgba(34,197,94,0.3)" : isError ? "rgba(239,68,68,0.25)" : "rgba(0,204,255,0.2)"}`,
        }}
      >
        <div
          style={{
            fontSize: 12,
            marginBottom: isActive ? 7 : 0,
            color: isDone ? "#22c55e" : isError ? "#ef4444" : "var(--fg)",
          }}
        >
          {stepLabel}
        </div>
        {isActive && (
          <div
            style={{
              height: 3,
              borderRadius: 2,
              background: "rgba(255,255,255,0.1)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: "55%",
                borderRadius: 2,
                background: barColor,
                animation: "lidar-progress 1.8s ease-in-out infinite",
              }}
            />
          </div>
        )}
        {isError && errorMessage && (
          <div
            style={{
              fontSize: 11,
              color: "#ef4444",
              marginTop: 4,
              opacity: 0.85,
            }}
          >
            {errorMessage}
          </div>
        )}
      </div>
    );
  };

  // ── Rendu de la liste des zones ───────────────────────────────────────

  const renderUploadsList = () => {
    if (uploads.length === 0) return null;

    return (
      <div style={{ marginTop: 10 }}>
        <div style={{ fontSize: 11, opacity: 0.45, marginBottom: 5 }}>
          {uploads.length === 1
            ? "1 zone chargée"
            : `${uploads.length} zones chargées`}
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          {uploads.map((u) => {
            const isDeleting = deletingId === u.id;
            return (
              <div
                key={u.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "7px 9px",
                  borderRadius: 6,
                  background: isDeleting
                    ? "rgba(239,68,68,0.06)"
                    : "rgba(255,255,255,0.05)",
                  border: `1px solid ${isDeleting ? "rgba(239,68,68,0.2)" : "rgba(255,255,255,0.08)"}`,
                  opacity: isDeleting ? 0.6 : 1,
                  transition: "all 0.2s",
                }}
              >
                {/* Icône */}
                <span style={{ fontSize: 14, flexShrink: 0 }}>
                  {u.file_exists ? "📦" : "⚠️"}
                </span>

                {/* Infos fichier */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      color: u.file_exists ? "var(--fg)" : "#f59e0b",
                    }}
                    title={u.original_filename}
                  >
                    {u.original_filename}
                  </div>
                  <div style={{ fontSize: 10, opacity: 0.45, marginTop: 1 }}>
                    {formatSize(u.file_size_mb)}
                    {u.uploaded_at ? ` · ${formatDate(u.uploaded_at)}` : ""}
                    {!u.file_exists && (
                      <span style={{ color: "#f59e0b", marginLeft: 4 }}>
                        · fichier manquant
                      </span>
                    )}
                  </div>
                </div>

                {/* Bouton supprimer */}
                <button
                  onClick={() =>
                    !isDeleting &&
                    !isProcessing &&
                    handleDeleteUpload(u.id, u.original_filename)
                  }
                  disabled={isDeleting || isProcessing || deletingId !== null}
                  title={
                    isProcessing
                      ? "Annulez le traitement avant de supprimer"
                      : "Supprimer cette zone"
                  }
                  style={{
                    flexShrink: 0,
                    width: 24,
                    height: 24,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 4,
                    border: "1px solid rgba(239,68,68,0.3)",
                    background: "transparent",
                    color:
                      isDeleting || isProcessing || deletingId !== null
                        ? "rgba(239,68,68,0.3)"
                        : "rgba(239,68,68,0.7)",
                    cursor:
                      isDeleting || isProcessing || deletingId !== null
                        ? "not-allowed"
                        : "pointer",
                    fontSize: 13,
                    lineHeight: 1,
                    padding: 0,
                    transition: "all 0.15s",
                  }}
                >
                  {isDeleting ? "⏳" : "✕"}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // ── Render ───────────────────────────────────────────────────────────

  return (
    <div style={{ marginTop: 12, fontSize: 13 }}>
      <style>{`
        @keyframes lidar-progress {
          0%   { transform: translateX(-100%); }
          50%  { transform: translateX(60%); }
          100% { transform: translateX(200%); }
        }
      `}</style>

      <span style={labelStyle}>📡 Données LIDAR</span>
      <span style={labelStyle}>
        <a href="https://cartes.gouv.fr/telechargement/IGNF_NUAGES-DE-POINTS-LIDAR-HD" target="_blank" rel="noopener noreferrer">
          Ou trouver un fichier LAZ ?
        </a>
      </span>

      {/* Zone de dépôt */}
      <div
        style={dropzoneStyle}
        onClick={() => canUpload && fileInputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (canUpload) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={canUpload ? handleDrop : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".laz,.las"
          style={{ display: "none" }}
          onChange={handleFileChange}
          disabled={!canUpload}
        />

        {uploading ? (
          <span style={{ opacity: 0.6, fontSize: 12 }}>⏳ Envoi en cours…</span>
        ) : isProcessing ? (
          <div>
            <div style={{ opacity: 0.5, fontSize: 12 }}>
              ⚙️ Traitement en cours…
            </div>
            <div style={{ opacity: 0.35, fontSize: 11, marginTop: 3 }}>
              Annulez avant d'ajouter une nouvelle zone
            </div>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 20, marginBottom: 3 }}>🗂️</div>
            <div style={{ opacity: 0.7, fontSize: 12 }}>
              Déposez un fichier <strong>.laz</strong> ici
            </div>
            <div style={{ opacity: 0.4, fontSize: 11, marginTop: 2 }}>
              ou cliquez pour sélectionner
            </div>
            {snowReady && (
              <div
                style={{
                  marginTop: 6,
                  fontSize: 11,
                  color: "#22c55e",
                  opacity: 0.8,
                }}
              >
                ❄️ Carte de neige active
              </div>
            )}
          </>
        )}
      </div>

      {/* Erreur upload */}
      {uploadError && (
        <div
          style={{
            marginTop: 7,
            padding: "7px 10px",
            borderRadius: 6,
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#ef4444",
            fontSize: 12,
          }}
        >
          ⚠️ {uploadError}
        </div>
      )}

      {/* Erreur suppression */}
      {deleteError && (
        <div
          style={{
            marginTop: 7,
            padding: "7px 10px",
            borderRadius: 6,
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#ef4444",
            fontSize: 12,
          }}
        >
          ⚠️ {deleteError}
        </div>
      )}

      {/* Liste des zones */}
      {renderUploadsList()}

      {/* Barre de progression pipeline */}
      {renderPipelineBar()}

      {/* Bouton annulation */}
      {isProcessing && (
        <button
          onClick={handleCancel}
          disabled={!canCancel}
          style={{
            marginTop: 8,
            width: "100%",
            padding: "7px 12px",
            borderRadius: 6,
            border: "1px solid rgba(239,68,68,0.4)",
            background: cancelling
              ? "rgba(239,68,68,0.05)"
              : "rgba(239,68,68,0.12)",
            color: cancelling ? "rgba(239,68,68,0.5)" : "#ef4444",
            fontSize: 12,
            fontWeight: 600,
            cursor: canCancel ? "pointer" : "not-allowed",
            transition: "all 0.2s",
          }}
        >
          {cancelling ? "⏳ Annulation en cours…" : "✕ Annuler le traitement"}
        </button>
      )}
    </div>
  );
}
