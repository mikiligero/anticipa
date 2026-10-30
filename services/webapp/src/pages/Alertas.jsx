import React from "react";
import { detalleIncidencia, LineaChip, NivelPill, Vacio, haceCuanto } from "../ui.jsx";

export default function Alertas({ alertas, leidas, marcarLeidas }) {
  const noLeidas = alertas.filter((a) => !leidas.includes(a.id)).length;
  return (
    <>
      <div className="saludo">{noLeidas > 0 ? `${noLeidas} sin leer` : "Todo leído"}</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1>Alertas</h1>
        {noLeidas > 0 && (
          <a href="#" style={{ color: "var(--magenta)", fontWeight: 700, textDecoration: "none" }}
             onClick={(e) => { e.preventDefault(); marcarLeidas(alertas.map((a) => a.id)); }}>
            Marcar leídas
          </a>
        )}
      </div>
      <div style={{ color: "var(--ink-3)", fontSize: ".78rem", marginBottom: 14 }}>
        Nivel: <NivelPill nivel="normal" conDot>Normal</NivelPill> <NivelPill nivel="leve" conDot>Leve</NivelPill>{" "}
        <NivelPill nivel="moderado" conDot>Moderado</NivelPill> <NivelPill nivel="grave" conDot>Grave</NivelPill>{" "}
        <NivelPill nivel="critico" conDot>Crítico</NivelPill>
      </div>

      {alertas.length === 0 && (
        <Vacio emoji="🔕">Sin alertas por ahora.<br />Se generan con las incidencias del feed y los retrasos en tus trayectos.</Vacio>
      )}

      {alertas.map((a) => (
        <div key={a.id} className={`card alerta b-${a.consejo ? "consejo" : a.nivel}`}>
          <div className="meta">
            {a.consejo
              ? <span className="tag consejo">Consejo</span>
              : <NivelPill nivel={a.nivel} conDot={false} />}
            <span className="cuando">{a.desde_ts ? haceCuanto(a.desde_ts) : a.desde ? `Desde ${a.desde}` : "Ahora"}</span>
            {!leidas.includes(a.id) && <span className="nodot" aria-label="Sin leer" />}
          </div>
          <div className="titulo">{a.titulo}</div>
          <div className="detalle">
            {a.lineas?.map((l) => <LineaChip key={l} linea={l} />)}{" "}
            {a.detalle || detalleIncidencia(a)}
          </div>
        </div>
      ))}
    </>
  );
}
