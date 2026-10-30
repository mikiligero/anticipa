import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import "./tendencias.css";

const hora = (ts) => new Date(ts * 1000).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Madrid" });
const numero = (n) => n == null ? "Sin datos" : n.toLocaleString("es-ES", { maximumFractionDigits: 1 });
const RETRASOS = [{ key: "retraso_medio_min", label: "Retraso medio", color: "#8a0a5a" }, { key: "retraso_p90_min", label: "Percentil 90", color: "#d95f16", dash: "6 4" }];
const PUNTUALIDAD = [{ key: "puntualidad_pct", label: "Trenes con retraso < 5 min", color: "#0a7d33" }];

function Grafica({ title, subtitle, serie, lines, porcentajes = false }) {
  const [hover, setHover] = useState(null);
  const values = serie.flatMap((r) => lines.map((l) => r[l.key])).filter((n) => n != null);
  const min = porcentajes ? 0 : Math.min(0, Math.floor(Math.min(...values, 0) / 5) * 5);
  const max = porcentajes ? 100 : Math.max(5, Math.ceil(Math.max(...values, 5) / 5) * 5);
  const x = (i) => 54 + i * 620 / Math.max(1, serie.length - 1);
  const y = (v) => 220 - (v - min) * 190 / (max - min);
  const latest = serie.reduce((last, r, i) => r.trenes ? i : last, null);
  const selected = serie[hover ?? latest];
  const path = (key) => {
    let d = "", connected = false;
    serie.forEach((r, i) => {
      if (r[key] == null) { connected = false; return; }
      d += `${connected ? "L" : "M"}${x(i)},${y(r[key])} `; connected = true;
    });
    return d;
  };
  return (
    <section className="card tendencia-card">
      <h3>{title}</h3><p className="tendencia-descripcion">{subtitle}</p>
      {values.length ? (
        <svg className="tendencia-svg" viewBox="0 0 710 260" aria-label={title} onMouseLeave={() => setHover(null)}>
          {[0, 1, 2, 3, 4].map((i) => {
            const v = min + i * (max - min) / 4;
            return <g key={i}><line x1="54" x2="674" y1={y(v)} y2={y(v)} stroke="#e7e8ec" /><text x="45" y={y(v) + 4} textAnchor="end">{numero(v)}{porcentajes ? "%" : "′"}</text></g>;
          })}
          {lines.map((l) => <g key={l.key}><path d={path(l.key)} stroke={l.color} fill="none" strokeWidth="3" strokeDasharray={l.dash} />{serie.map((r, i) => r[l.key] != null && <circle key={i} cx={x(i)} cy={y(r[l.key])} r="3" fill={l.color} />)}</g>)}
          {hover != null && <line x1={x(hover)} x2={x(hover)} y1="25" y2="220" stroke="#9aa0aa" strokeDasharray="3 3" />}
          {serie.map((r, i) => <g key={r.ts}>
            {(i % 6 === 0 || i === serie.length - 1) && <text x={x(i)} y="246" textAnchor="middle">{hora(r.ts)}</text>}
            <rect x={x(i) - 13} y="20" width="26" height="205" fill="transparent" tabIndex="0" role="button" aria-label={`${hora(r.ts)}: ${r.trenes} trenes. ${lines.map((l) => `${l.label}: ${numero(r[l.key])}`).join(". ")}`} onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} />
          </g>)}
        </svg>
      ) : <div className="tendencia-vacia">Aún no hay observaciones suficientes en este núcleo durante las últimas 2 horas.</div>}
      <div className="tendencia-leyenda">{lines.map((l) => <span key={l.key}><i style={{ borderColor: l.color, borderTopStyle: l.dash ? "dashed" : "solid" }} />{l.label}</span>)}</div>
      {selected && <div className="tendencia-detalle" role="status"><b>{hora(selected.ts)}–{hora(selected.ts + 300)}{selected.en_curso ? " · en curso" : ""}</b><span>{selected.trenes} {selected.trenes === 1 ? "tren observado" : "trenes observados"}</span>{lines.map((l) => <span key={l.key}>{l.label}: <b>{numero(selected[l.key])}{selected[l.key] == null ? "" : porcentajes ? "%" : " min"}</b></span>)}</div>}
    </section>
  );
}

export default function Tendencias({ nucleo }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController(); let timer;
    const load = async () => {
      try {
        const r = await api.tendencias(nucleo, controller.signal);
        if (controller.signal.aborted) return;
        if (r.nucleo !== nucleo) throw new Error("Núcleo inesperado");
        setData(r); setError(false);
      } catch (e) { if (!controller.signal.aborted) { setError(true); setData(null); } }
      if (!controller.signal.aborted) timer = setTimeout(load, 60000);
    };
    load(); return () => { controller.abort(); clearTimeout(timer); };
  }, [nucleo]);
  return (
    <section className="tendencias" aria-label={`Tendencias de ${nucleo}`}>
      <div className="tendencias-cabecera"><h2>Tendencias · {nucleo}</h2><span>Últimas 2 horas · intervalos de 5 minutos</span></div>
      {error ? <div className="card" role="status">No se pudieron cargar las tendencias. Reintentando…</div> : !data ? <div className="card" role="status">Cargando el histórico reciente…</div> : <>
        <div className="tendencias-grid">
          <Grafica title="Evolución del retraso" subtitle="Media y percentil 90 de los retrasos observados, en minutos." serie={data.serie} lines={RETRASOS} />
          <Grafica title="Evolución de la puntualidad" subtitle="Porcentaje de trenes con menos de 5 minutos de retraso." serie={data.serie} lines={PUNTUALIDAD} porcentajes />
        </div>
        <p className="tendencias-nota">Datos reales · un registro por viaje en cada intervalo · los huecos indican falta de observaciones. El último intervalo está en curso. Actualizado {hora(data.actualizado_ts)}.</p>
      </>}
    </section>
  );
}
