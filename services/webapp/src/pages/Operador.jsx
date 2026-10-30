/**
 * Centro de Control — vista desktop para operadores de Cercanías.
 * Misma plataforma y servidor que la app de viajero; datos reales y predicciones de ejemplo identificadas:
 * estado en vivo, incidencias del feed, mapa, tendencias y predicciones simuladas.
 */
import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { PREDICCION_OPERADOR as DEMO } from "../demo/predicciones.js";
import AvisoSimulacion from "../demo/AvisoSimulacion.jsx";
import MapaRed from "../mapa/MapaRed.jsx";
import Tendencias from "../tendencias/Tendencias.jsx";
import { Escala, LineaChip, NivelPill, NIVEL_LABEL } from "../ui.jsx";
import { NIVEL_ORDEN } from "../storage.js";

const POLL_MS = 30000;

export default function Operador() {
  const [nucleo, setNucleo] = useState("Madrid");
  const [nucleos, setNucleos] = useState(["Madrid"]);
  const [resumen, setResumen] = useState(null);
  const [lineas, setLineas] = useState([]);
  const [incidencias, setIncidencias] = useState([]);
  const [hora, setHora] = useState(new Date());
  const [lineaAbierta, setLineaAbierta] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.nucleos().then((n) => n.length && setNucleos(n)).catch(() => {});
    const t = setInterval(() => setHora(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let vivo = true;
    const cargar = async () => {
      try {
        const [r, l, i] = await Promise.all([
          api.resumen(nucleo), api.lineas(nucleo), api.incidencias(nucleo),
        ]);
        if (!vivo) return;
        setResumen(r); setLineas(l); setIncidencias(i); setError(null);
      } catch (e) {
        if (vivo) setError(String(e));
      }
    };
    cargar();
    const t = setInterval(cargar, POLL_MS);
    return () => { vivo = false; clearInterval(t); };
  }, [nucleo]);

  const afectadas = lineas.filter((l) => (NIVEL_ORDEN[l.nivel] ?? 0) >= 2).length;
  const graves = incidencias.filter((i) => ["grave", "critico"].includes(i.nivel)).length;
  return (
    <div className="op-root">
      {/* ── Cabecera ── */}
      <header className="op-header">
        <div className="op-title">
          <img src="/logo.svg" alt="" width="36" height="36" />
          <div>
            <h1>Centro de Control · Cercanías {nucleo}</h1>
            <span>Monitorización en tiempo real · anticipa</span>
          </div>
        </div>
        <div className="op-header-right">
          <span className="op-clock">
            {hora.toLocaleTimeString("es-ES")} · {hora.toLocaleDateString("es-ES", { day: "2-digit", month: "short" })}
          </span>
          <select className="op-select" value={nucleo} onChange={(e) => setNucleo(e.target.value)}>
            {nucleos.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </header>

      {error && <div className="card" style={{ color: "var(--nv-grave)" }}>API no disponible: {error}</div>}

      {/* ── Tiles ── */}
      <div className="op-tiles">
        <Tile v={resumen?.puntualidad_pct != null ? `${resumen.puntualidad_pct}%` : "—"}
              k="Puntualidad red (ahora)" tone={resumen?.puntualidad_pct >= 80 ? "ok" : resumen?.puntualidad_pct >= 60 ? "warn" : "bad"} />
        <Tile v={resumen?.retraso_medio_min != null ? `+${resumen.retraso_medio_min}'` : "—"}
              k="Retraso medio" tone={resumen?.retraso_medio_min < 4 ? "ok" : resumen?.retraso_medio_min < 8 ? "warn" : "bad"} />
        <Tile v={resumen?.viajes_activos ?? "—"} k="Trenes activos" />
        <Tile v={incidencias.length} k={graves ? `Incidencias · ${graves} graves` : "Incidencias"} tone={graves ? "bad" : incidencias.length ? "warn" : "ok"} />
        <Tile v={DEMO.alertas} k="Alertas simuladas (≥90%)" tone="warn" />
      </div>

      <MapaRed key={`mapa-${nucleo}`} nucleo={nucleo} />

      <div className="op-main">
        {/* ── Columna izquierda ── */}
        <div>
          <section className="card">
            <div className="op-sec-head">
              <b>📈 Predicciones de la red</b>
              <span>Vista de ejemplo · predicción simulada</span>
            </div>
            <div className="op-pred alerta b-grave">
              <div className="op-pred-head">
                <b>Línea de ejemplo</b>
                <NivelPill nivel="grave" conDot={false} />
                <span className="op-dim">Ejemplo · horizonte fin de trayecto</span>
              </div>
              <b>Retraso final de hasta +{DEMO.retrasoFinal} min</b>
              <div className="op-dim">{DEMO.alertas} de {DEMO.trenes} trenes con alerta · valores ficticios para la demostración</div>
              <div className="op-pred-foot">
                <span>Probabilidad <b style={{ color: "var(--nv-grave)" }}>{DEMO.probabilidad}%</b></span>
                <div className="op-barra"><div style={{ width: `${DEMO.probabilidad}%` }} /></div>
                <span className="op-dim">Confianza {DEMO.confianza} · ejemplo simulado</span>
              </div>
            </div>
            <AvisoSimulacion />
          </section>

          <section className="card">
            <div className="op-sec-head"><b>Estado por línea</b><span>clic en una línea para ver sus trenes y estaciones</span></div>
            <table className="op-tabla">
              <thead>
                <tr><th>Línea</th><th>Trayecto</th><th>Punt.</th><th>Retraso</th><th>Trenes</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {lineas.map((l) => {
                  const abierta = lineaAbierta === l.linea;
                  return (
                    <React.Fragment key={l.linea}>
                      <tr className={`op-fila ${abierta ? "abierta" : ""}`}
                          onClick={() => setLineaAbierta(abierta ? null : l.linea)}>
                        <td><LineaChip linea={l.linea} /></td>
                        <td className="op-trayecto"><span className={`op-dot d-${l.nivel}`} /> {l.nombre || "—"} <span className="op-dim">{abierta ? "▲" : "▼"}</span></td>
                        <td className={l.puntualidad_pct >= 80 ? "ok" : l.puntualidad_pct >= 60 ? "warn" : "bad"}>{l.puntualidad_pct}%</td>
                        <td className={l.retraso_medio_min < 4 ? "ok" : l.retraso_medio_min < 8 ? "warn" : "bad"}>+{l.retraso_medio_min}'</td>
                        <td>{l.trenes_activos}</td>
                        <td>
                          {(NIVEL_ORDEN[l.nivel] ?? 0) <= 1
                              ? <NivelPill nivel="normal" conDot={false}>Estable</NivelPill>
                              : <NivelPill nivel={l.nivel} conDot={false} />}
                        </td>
                      </tr>
                      {abierta && (
                        <tr>
                          <td colSpan={6} style={{ padding: 0, background: "#fbfbfc" }}>
                            <LineaDetalleOp linea={l.linea} nucleo={nucleo} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </section>
        </div>

        {/* ── Columna derecha ── */}
        <div>
          <section className="card">
            <div className="op-sec-head">
              <b>🚦 Estado global de la red</b>
              <span style={{ display: "inline-flex", alignItems: "baseline", gap: 8, padding: "10px 16px", borderRadius: 12, background: "#fff1e6", color: "#913b08", fontSize: "1rem", fontWeight: 700, flexWrap: "wrap" }}><strong style={{ fontSize: "1.8rem", lineHeight: 1.1 }}>{afectadas}/{lineas.length}</strong> líneas afectadas</span>
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 800, margin: "4px 0 2px" }}>
              {resumen ? NIVEL_LABEL[resumen.nivel] : "—"}
            </div>
            {resumen && <Escala nivel={resumen.nivel} />}
          </section>

          <section className="card">
            <div className="op-sec-head"><b>Incidencias activas</b><span>feed service_alerts</span></div>
            {incidencias.length === 0 && <div className="op-vacio">Sin incidencias activas.</div>}
            {incidencias.map((i) => (
              <div key={i.id} className={`op-inci alerta b-${i.nivel}`}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 3 }}>
                  {i.lineas.slice(0, 3).map((l) => <LineaChip key={l} linea={l} />)}
                  <NivelPill nivel={i.nivel} conDot={false} />
                  {i.desde && <span className="op-dim">desde {i.desde}</span>}
                </div>
                <div className="op-inci-titulo">{i.titulo}</div>
              </div>
            ))}
          </section>

        </div>
      </div>
      <Tendencias key={`tendencias-${nucleo}`} nucleo={nucleo} />
    </div>
  );
}

function Tile({ v, k, tone }) {
  return (
    <div className="tile">
      <div className={`v ${tone || ""}`}>{v}</div>
      <div className="k">{k}</div>
    </div>
  );
}

/** Detalle de línea expandido en la tabla del operador. */
function LineaDetalleOp({ linea, nucleo }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [trenAbierto, setTrenAbierto] = useState(null);

  useEffect(() => {
    let vivo = true;
    setData(null); setError(null); setTrenAbierto(null);
    api.linea(linea, nucleo).then((d) => vivo && setData(d)).catch((e) => vivo && setError(e.message));
    return () => { vivo = false; };
  }, [linea, nucleo]);

  if (error) return <div className="op-vacio">Sin datos de {linea} ahora mismo.</div>;
  if (!data) return <div className="op-vacio">Cargando {linea}…</div>;

  return (
    <div className="op-lindet">
      <div className="op-lindet-grid">
        <div>
          <div className="op-dim" style={{ fontWeight: 700, marginBottom: 6 }}>TRENES EN VÍA ({data.trenes.length})</div>
          {data.trenes.map((t) => (
            <div key={t.trip_id}>
              <div className="op-tren-fila" onClick={() => setTrenAbierto(trenAbierto === t.trip_id ? null : t.trip_id)}>
                <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontWeight: 700 }}>{t.llegada || "—:—"}</span>
                <span style={{ flex: 1 }} className="op-trayecto">
                  {t.destino ? `a ${t.destino}` : t.trip_id} <span className="op-dim">· próx. {t.proxima_parada}</span>
                </span>
                <NivelPill nivel={t.nivel} conDot={false}>
                  {t.retraso_min != null && t.retraso_min >= 2 ? `+${Math.round(t.retraso_min)}'` : "En hora"}
                </NivelPill>
              </div>
              {trenAbierto === t.trip_id && <TrenDetalleOp tripId={t.trip_id} />}
            </div>
          ))}
        </div>
        <div>
          <div className="op-dim" style={{ fontWeight: 700, marginBottom: 6 }}>ESTACIONES · SEMÁFORO</div>
          {data.estaciones.map((e) => (
            <div key={e.stop_id} className="op-tren-fila" style={{ cursor: "default" }}>
              <span className={`op-dot d-${e.nivel}`} />
              <span style={{ flex: 1, fontWeight: 600 }}>{e.nombre}</span>
              <span className="op-dim">{e.n_trenes} 🚆</span>
              <NivelPill nivel={e.nivel} conDot={false}>
                {e.retraso_medio_min < 2 ? "Normal" : `+${Math.round(e.retraso_medio_min)}'`}
              </NivelPill>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Datos en vivo de un tren, inline en el panel del operador. */
function TrenDetalleOp({ tripId }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    let vivo = true;
    setData(null);
    api.tren(tripId).then((d) => vivo && setData(d)).catch(() => vivo && setData({ error: true }));
    return () => { vivo = false; };
  }, [tripId]);

  if (!data) return <div className="op-vacio" style={{ padding: "8px 12px" }}>Cargando tren…</div>;
  if (data.error) return <div className="op-vacio" style={{ padding: "8px 12px" }}>Tren ya no disponible.</div>;

  const t = data.tren;
  return (
    <div className="op-trendet">
      <span>Próxima parada: <b>{t.proxima_parada || "—"}</b></span>
      <span className="op-dim"> · llegada estimada {t.llegada || "—:—"}</span>
      <span className="op-dim"> · retraso actual {t.retraso_min == null ? "sin dato" : `${Math.round(t.retraso_min)} min`}</span>
    </div>
  );
}
