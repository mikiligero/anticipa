// Componentes compartidos de la app
import React from "react";

export const NIVEL_LABEL = {
  normal: "Normal", leve: "Leve", moderado: "Moderado", grave: "Grave", critico: "Crítico",
};
const NIVELES = ["normal", "leve", "moderado", "grave", "critico"];

// Colores fijos por línea (identidad estable, no por orden de llegada)
const LINEA_COLORES = {
  C1: "#2a78d6", C2: "#008300", C3: "#4a3aa7", C4: "#1c3f94", C4a: "#1c3f94", C4b: "#1c3f94",
  C5: "#eda100", C7: "#e34948", C8: "#6b7280", C8a: "#6b7280", C8b: "#6b7280",
  C9: "#eb6834", C10: "#1baf7a",
};
export function colorLinea(linea) {
  return LINEA_COLORES[linea] || "#8a0a5a";
}

export function LineaChip({ linea }) {
  if (!linea) return <span className="linea-chip" style={{ background: "#9aa0aa" }}>—</span>;
  return <span className="linea-chip" style={{ background: colorLinea(linea) }}>{linea}</span>;
}

export function NivelPill({ nivel, conDot = true, children }) {
  return (
    <span className={`pill nv-${nivel || "normal"}`}>
      {conDot && <span className="dot" aria-hidden="true" />}
      {children ?? NIVEL_LABEL[nivel] ?? nivel}
    </span>
  );
}

export function RetrasoPill({ min }) {
  if (min == null) return <NivelPill nivel="normal" conDot={false}>Sin dato</NivelPill>;
  if (min < 2) return <NivelPill nivel="normal" conDot={false}>En hora</NivelPill>;
  const nivel = min < 4 ? "leve" : min < 8 ? "moderado" : min < 15 ? "grave" : "critico";
  return <NivelPill nivel={nivel} conDot={false}>{`+${Math.round(min)} min`}</NivelPill>;
}

export function Escala({ nivel }) {
  return (
    <>
      <div className="escala" role="img" aria-label={`Nivel de servicio: ${NIVEL_LABEL[nivel]}`}>
        {NIVELES.map((n) => (
          <div key={n} className={`seg ${NIVELES.indexOf(n) <= NIVELES.indexOf(nivel) ? `on-${n}` : ""}`} />
        ))}
      </div>
      <div className="escala-labels">
        {NIVELES.map((n) => (
          <span key={n} className={n === nivel ? `on ${n}` : ""}>{NIVEL_LABEL[n]}</span>
        ))}
      </div>
    </>
  );
}

export function Vacio({ emoji, children }) {
  return (
    <div className="vacio">
      <div className="e" aria-hidden="true">{emoji}</div>
      {children}
    </div>
  );
}

export function haceCuanto(ts) {
  if (!ts) return "";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 90) return "Hace 1 min";
  if (s < 3600) return `Hace ${Math.round(s / 60)} min`;
  if (s < 86400) return `Hace ${Math.round(s / 3600)} h`;
  return "Ayer o antes";
}

export function detalleIncidencia(incidencia) {
  return [incidencia.causa, incidencia.efecto]
    .filter((texto) => texto && !/desconocid[oa]/i.test(texto))
    .join(" · ");
}
