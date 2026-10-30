import React, { useState } from "react";
import { LineaChip, NivelPill, Vacio } from "../ui.jsx";

export default function Trayectos({ profile, setProfile, lineas, estaciones }) {
  const [creando, setCreando] = useState(false);

  const toggleAlertas = (id) => {
    setProfile({
      ...profile,
      trayectos: profile.trayectos.map((t) => (t.id === id ? { ...t, alertas: !t.alertas } : t)),
    });
  };

  const borrar = (id) => {
    setProfile({ ...profile, trayectos: profile.trayectos.filter((t) => t.id !== id) });
  };

  const nivelLinea = (linea) => lineas.find((l) => l.linea === linea)?.nivel || "normal";
  const retrasoLinea = (linea) => lineas.find((l) => l.linea === linea)?.retraso_medio_min;

  if (creando) {
    return (
      <NuevoTrayecto
        lineas={lineas}
        estaciones={estaciones}
        onCancel={() => setCreando(false)}
        onSave={(t) => {
          setProfile({ ...profile, trayectos: [...profile.trayectos, t] });
          setCreando(false);
        }}
      />
    );
  }

  return (
    <>
      <div className="saludo">Tus rutas habituales</div>
      <h1>Mis trayectos</h1>

      <button className="crear" onClick={() => setCreando(true)}>
        <span className="plus">+</span>
        <span>
          <b>Crear alerta de trayecto</b>
          <small>Avísame de retrasos en mi ruta</small>
        </span>
        <span className="chev" style={{ marginLeft: "auto" }}>›</span>
      </button>
      <div style={{ height: 14 }} />

      {profile.trayectos.length === 0 && (
        <Vacio emoji="🧭">Aún no tienes trayectos guardados.<br />Crea el primero para recibir avisos de tu ruta.</Vacio>
      )}

      {profile.trayectos.map((t) => {
        const retraso = retrasoLinea(t.linea);
        return (
          <div key={t.id} className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <LineaChip linea={t.linea} />
              <b style={{ flex: 1 }}>{t.nombre}</b>
              {retraso != null && retraso >= 2 ? (
                <NivelPill nivel={nivelLinea(t.linea)} conDot={false}>{`+${Math.round(retraso)} min`}</NivelPill>
              ) : (
                <NivelPill nivel="normal" conDot={false}>En hora</NivelPill>
              )}
            </div>
            <div style={{ margin: "12px 0", fontWeight: 700 }}>
              {t.origen?.nombre} <span style={{ color: "var(--ink-3)" }}>→</span> {t.destinoLabel}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
              <span style={{ color: t.alertas ? "var(--magenta)" : "var(--ink-3)" }}>🔔</span>
              <span style={{ color: "var(--ink-2)", fontSize: ".9rem", flex: 1 }}>{t.franja || "Cualquier hora"}</span>
              <button className="btn plano" style={{ width: "auto", padding: "4px 8px", fontSize: ".8rem" }} onClick={() => borrar(t.id)}>
                Eliminar
              </button>
              <label className="switch">
                <input type="checkbox" checked={!!t.alertas} onChange={() => toggleAlertas(t.id)} />
                <span />
              </label>
            </div>
          </div>
        );
      })}
      <div className="footer-nota">
        El estado del trayecto refleja el retraso medio actual de su línea (dato GTFS-RT en vivo).
      </div>
    </>
  );
}

function NuevoTrayecto({ lineas, estaciones, onCancel, onSave }) {
  const [nombre, setNombre] = useState("");
  const [linea, setLinea] = useState("");
  const [origenId, setOrigenId] = useState("");
  const [destinoLabel, setDestinoLabel] = useState("");
  const [franja, setFranja] = useState("L–V · 07:30–09:30");

  const guardar = () => {
    const origen = estaciones.find((e) => e.stop_id === origenId);
    if (!nombre || !origen) return;
    onSave({
      id: `${Date.now()}`,
      nombre,
      linea: linea || null,
      origen,
      destinoLabel: destinoLabel || "Destino",
      franja,
      alertas: true,
    });
  };

  return (
    <>
      <div className="cab-detalle">
        <button className="volver" onClick={onCancel} aria-label="Volver">‹</button>
        <h2>Nuevo trayecto</h2>
      </div>
      <div className="card">
        <div className="field">
          <label>Nombre</label>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Casa → Trabajo" />
        </div>
        <div className="field">
          <label>Estación de origen (donde te subes)</label>
          <select value={origenId} onChange={(e) => setOrigenId(e.target.value)}>
            <option value="">— Elegir (estaciones con trenes ahora) —</option>
            {estaciones.map((e) => (
              <option key={e.stop_id} value={e.stop_id}>{e.nombre}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Línea (opcional)</label>
          <select value={linea} onChange={(e) => setLinea(e.target.value)}>
            <option value="">Todas</option>
            {lineas.map((l) => (
              <option key={l.linea} value={l.linea}>{l.linea} — {l.nombre}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Destino (etiqueta)</label>
          <input value={destinoLabel} onChange={(e) => setDestinoLabel(e.target.value)} placeholder="Nuevos Ministerios" />
        </div>
        <div className="field">
          <label>Franja de aviso</label>
          <input value={franja} onChange={(e) => setFranja(e.target.value)} />
        </div>
        <button className="btn primario" onClick={guardar} disabled={!nombre || !origenId}>Guardar trayecto</button>
        <button className="btn plano" onClick={onCancel}>Cancelar</button>
      </div>
      <div className="footer-nota">
        El selector muestra estaciones a las que se aproxima algún tren ahora mismo (única fuente: feed en vivo).
      </div>
    </>
  );
}
