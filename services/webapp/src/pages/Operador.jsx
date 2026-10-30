/**
 * Centro de Control — vista desktop para operadores de Cercanías.
 * Misma plataforma y servidor que la app de viajero; datos reales y predicciones de ejemplo identificadas:
 * ruta caliente (estado), modelo predictivo (/api-op/prediccion, token
 * inyectado por nginx), incidencias del feed, mapa y tendencias.
 */
import React, { useEffect, useMemo, useState } from "react";
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
  const [pred, setPred] = useState(null);
  const [hora, setHora] = useState(new Date());
  const [emitidos, setEmitidos] = useState({});
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
        try {
          setPred(await api.prediccionRed(nucleo));
        } catch {
          setPred(null); // sin modelo en prod: la vista lo indica
        }
      } catch (e) {
        if (vivo) setError(String(e));
      }
    };
    cargar();
    const t = setInterval(cargar, POLL_MS);
    return () => { vivo = false; clearInterval(t); };
  }, [nucleo]);

  // ── Agregación de predicciones del modelo por línea ────────────────────
  const predLineas = useMemo(() => {
    if (!pred?.predicciones?.length) return [];
    const grupos = {};
    for (const p of pred.predicciones) {
      const l = p.linea || "—";
      grupos[l] ??= { linea: l, trenes: 0, alertas: 0, maxProb: 0, maxPred: null, paradas: {} };
      const g = grupos[l];
      g.trenes += 1;
      if (p.alerta) {
        g.alertas += 1;
        g.maxProb = Math.max(g.maxProb, p.prob_retraso_grave);
        g.maxPred = Math.max(g.maxPred ?? 0, p.retraso_final_previsto_min);
        if (p.stop_name) g.paradas[p.stop_name] = (g.paradas[p.stop_name] || 0) + 1;
      }
    }
    return Object.values(grupos)
      .filter((g) => g.alertas > 0)
      .map((g) => ({
        ...g,
        nivel: g.maxPred >= 15 ? "critico" : g.maxPred >= 8 ? "grave" : "moderado",
        confianza: g.maxProb >= 0.95 ? "Alta" : "Media",
        parada: Object.entries(g.paradas).sort((a, b) => b[1] - a[1])[0]?.[0],
      }))
      .sort((a, b) => b.maxProb - a.maxProb || b.maxPred - a.maxPred);
  }, [pred]);

  const prioritaria = predLineas[0];
  const afectadas = lineas.filter((l) => (NIVEL_ORDEN[l.nivel] ?? 0) >= 2).length;
  const graves = incidencias.filter((i) => ["grave", "critico"].includes(i.nivel)).length;
  const predPorLinea = Object.fromEntries(predLineas.map((g) => [g.linea, g]));

  const emitir = (id) => setEmitidos((e) => ({ ...e, [id]: true }));

  return (
    <div className="op-root">
      {/* ── Cabecera ── */}
      <header className="op-header">
        <div className="op-title">
          <img src="/logo.svg" alt="" width="36" height="36" />
          <div>
            <h1>Centro de Control · Cercanías {nucleo}</h1>
            <span>Monitorización y predicción en tiempo real · anticipa</span>
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
        <Tile v={pred ? pred.alertas.length : DEMO.alertas} k={pred ? "Alertas del modelo (≥90%)" : "Alertas simuladas (≥90%)"} tone={pred ? (pred.alertas.length ? "warn" : "ok") : "warn"} />
      </div>

      <MapaRed key={`mapa-${nucleo}`} nucleo={nucleo} />

      <div className="op-main">
        {/* ── Columna izquierda ── */}
        <div>
          <section className="card">
            <div className="op-sec-head">
              <b>📈 Predicciones de la red</b>
              <span>{pred ? `modelo LightGBM · MAE ${pred.modelo?.mae_min ?? "—"} min · umbral de emisión ≥ ${Math.round((pred.umbral_confianza ?? 0.9) * 100)}%` : "Vista de ejemplo · sin modelo activo"}</span>
            </div>
            {!pred && (
              <>
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
              </>
            )}
            {pred && predLineas.length === 0 && (
              <div className="op-vacio">No hay alertas del modelo por encima del umbral de emisión.</div>
            )}
            {predLineas.map((g) => (
              <div key={g.linea} className={`op-pred alerta b-${g.nivel}`}>
                <div className="op-pred-head">
                  <LineaChip linea={g.linea} />
                  <NivelPill nivel={g.nivel} conDot={false} />
                  <span className="op-dim">en curso · horizonte fin de trayecto</span>
                </div>
                <b>Retraso final de hasta +{Math.round(g.maxPred)} min previsto en {g.linea}</b>
                <div className="op-dim">
                  {g.alertas} de {g.trenes} trenes con alerta{g.parada ? ` · zona más afectada: ${g.parada}` : ""}
                </div>
                <div className="op-pred-foot">
                  <span>Probabilidad <b style={{ color: "var(--nv-grave)" }}>{Math.round(g.maxProb * 100)}%</b></span>
                  <div className="op-barra"><div style={{ width: `${g.maxProb * 100}%` }} /></div>
                  <span className="op-dim">Confianza {g.confianza} · {g.trenes} trayectos en vivo</span>
                  <button
                    className={`op-btn ${emitidos[g.linea] ? "hecho" : ""}`}
                    disabled={!!emitidos[g.linea]}
                    onClick={() => emitir(g.linea)}
                  >
                    {emitidos[g.linea] ? "✓ Aviso emitido" : "Emitir aviso"}
                  </button>
                </div>
              </div>
            ))}
          </section>

          <section className="card">
            <div className="op-sec-head"><b>Estado por línea</b><span>clic en una línea para ver sus trenes y predicción</span></div>
            <table className="op-tabla">
              <thead>
                <tr><th>Línea</th><th>Trayecto</th><th>Punt.</th><th>Retraso</th><th>Trenes</th><th>Predicción</th></tr>
              </thead>
              <tbody>
                {lineas.map((l) => {
                  const p = predPorLinea[l.linea];
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
                          {p
                            ? <NivelPill nivel={p.nivel} conDot={false}>{`▲ +${Math.round(p.maxPred)}'`}</NivelPill>
                            : (NIVEL_ORDEN[l.nivel] ?? 0) <= 1
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

          {prioritaria && (
            <section className="op-prioritaria">
              <div className="mini">⚠ PREDICCIÓN PRIORITARIA</div>
              <div className="op-prio-num">
                {Math.round(prioritaria.maxProb * 100)}% <LineaChip linea={prioritaria.linea} />
              </div>
              <b>Retraso final de hasta +{Math.round(prioritaria.maxPred)} min en {prioritaria.linea}</b>
              <div className="mini" style={{ marginTop: 6 }}>
                {prioritaria.alertas} trenes con alerta emitida por el modelo
                {prioritaria.parada ? ` · zona: ${prioritaria.parada}` : ""} · confianza {prioritaria.confianza}.
              </div>
              <div className="op-prio-botones">
                <button className="op-btn blanco" disabled={!!emitidos["protocolo"]} onClick={() => emitir("protocolo")}>
                  {emitidos["protocolo"] ? "✓ Protocolo activado" : "Activar protocolo"}
                </button>
                <button className="op-btn ghost" disabled={!!emitidos["notif"]} onClick={() => emitir("notif")}>
                  {emitidos["notif"] ? "✓ Viajeros notificados" : "Notificar viajeros"}
                </button>
              </div>
            </section>
          )}

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

          <div className="op-dim" style={{ textAlign: "center", padding: "6px 0 20px" }}>
            Los botones de aviso/protocolo son demostrativos (piloto): registran la acción localmente.
          </div>
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
      {data.prediccion && (
        <div className="op-lindet-pred">
          <b>Predicción de línea:</b> retraso final medio +{Math.round(data.prediccion.retraso_final_medio_min)}'
          · peor tren +{Math.round(data.prediccion.retraso_final_max_min)}'
          · <NivelPill nivel={data.prediccion.nivel_previsto} conDot={false} />
          {data.prediccion.n_alertas > 0 && <span className="bad"> · {data.prediccion.n_alertas} alertas del modelo</span>}
        </div>
      )}

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
                {t.retraso_final_previsto_min != null && (
                  <span className="op-dim">prev. +{Math.round(t.retraso_final_previsto_min)}'</span>
                )}
                <NivelPill nivel={t.nivel} conDot={false}>
                  {t.retraso_min != null && t.retraso_min >= 2 ? `+${Math.round(t.retraso_min)}'` : "En hora"}
                </NivelPill>
                {t.alerta && <span title="Alerta del modelo">⚠️</span>}
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

/** Predicción de un tren, inline en el panel del operador. */
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

  const p = data.prediccion;
  return (
    <div className="op-trendet">
      {p ? (
        <>
          <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "center" }}>
            <span><b>{p.prob_llegar_bien}%</b> <span className="op-dim">prob. sin retraso grave</span></span>
            <span><b>+{Math.round(p.retraso_final_min)}'</b> <span className="op-dim">retraso final est.</span></span>
            <span className="op-dim">confianza {p.confianza}</span>
            <NivelPill nivel={p.nivel_previsto} conDot={false} />
            {p.alerta && <NivelPill nivel="grave" conDot={false}>ALERTA EMITIDA</NivelPill>}
          </div>
          {data.proximas_estaciones?.length > 0 && (
            <div className="op-trendet-est">
              {data.proximas_estaciones.map((e, i) => (
                <span key={i} className="op-est-chip">
                  <span className={`op-dot d-${e.nivel}`} /> {e.nombre}
                  {e.hora_prevista && <span className="op-dim">{e.hora_prevista}</span>}
                  <b>+{Math.round(e.retraso_previsto_min)}'</b>
                </span>
              ))}
            </div>
          )}
        </>
      ) : (
        <span className="op-dim">Sin modelo en producción.</span>
      )}
    </div>
  );
}
