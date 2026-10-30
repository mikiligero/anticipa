import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Escala, LineaChip, NIVEL_LABEL, NivelPill, RetrasoPill, Vacio, colorLinea } from "../ui.jsx";

export default function Linea({ linea, nucleo, lineas, onNav, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let vivo = true;
    setData(null); setError(null);
    const cargar = () =>
      api.linea(linea, nucleo).then((d) => vivo && setData(d)).catch((e) => vivo && setError(e.message));
    cargar();
    const t = setInterval(cargar, 30000);
    return () => { vivo = false; clearInterval(t); };
  }, [linea, nucleo]);

  return (
    <>
      <div className="cab-detalle">
        <button className="volver" onClick={onBack} aria-label="Volver">‹</button>
        <div>
          <div style={{ color: "var(--ink-3)", fontSize: ".8rem", fontWeight: 600 }}>Dashboard de línea</div>
          <h2><LineaChip linea={linea} /> {data?.nombre || ""}</h2>
        </div>
      </div>

      {/* chips de líneas del núcleo */}
      <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 10, marginBottom: 6 }}>
        {lineas.map((l) => (
          <button
            key={l.linea}
            onClick={() => onNav({ name: "linea", linea: l.linea })}
            style={{
              border: 0, borderRadius: 12, padding: "8px 14px", fontWeight: 800, cursor: "pointer",
              whiteSpace: "nowrap",
              background: l.linea === linea ? colorLinea(l.linea) : "#fff",
              color: l.linea === linea ? "#fff" : "var(--ink)",
              boxShadow: "var(--shadow)",
            }}
          >
            {l.linea}
          </button>
        ))}
      </div>

      {error && <Vacio emoji="🚫">Sin trenes de {linea} en circulación ahora mismo.</Vacio>}
      {!data && !error && <Vacio emoji="⏳">Cargando línea…</Vacio>}

      {data && (
        <>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 800, fontSize: ".8rem", letterSpacing: ".6px", color: "var(--ink-2)" }}>🚦 ESTADO DE LA LÍNEA</span>
              <span className="envivo" style={{ color: "var(--nv-normal)" }}>EN VIVO</span>
            </div>
            <div style={{ fontSize: "1.4rem", fontWeight: 800, margin: "6px 0 0" }}>{NIVEL_LABEL[data.nivel]}</div>
            <Escala nivel={data.nivel} />
            <div style={{ color: "var(--ink-2)", fontSize: ".88rem", marginTop: 10 }}>
              Retraso medio de {data.retraso_medio_min} min en los {data.trenes_activos} trenes en vía
              {data.retraso_max_min >= 8 ? ` · máximo +${Math.round(data.retraso_max_min)} min` : ""}.
            </div>
          </div>

          <div className="tiles" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
            <div className="tile"><div className={`v ${data.puntualidad_pct >= 80 ? "ok" : data.puntualidad_pct >= 60 ? "warn" : "bad"}`}>{data.puntualidad_pct}%</div><div className="k">Puntualidad ahora</div></div>
            <div className="tile"><div className={`v ${data.retraso_medio_min < 4 ? "ok" : data.retraso_medio_min < 8 ? "warn" : "bad"}`}>+{data.retraso_medio_min}'</div><div className="k">Retraso medio</div></div>
            <div className="tile"><div className="v">{data.trenes_activos}</div><div className="k">Trenes en vía</div></div>
            <div className="tile"><div className={`v ${data.retraso_max_min < 8 ? "ok" : "bad"}`}>+{Math.round(data.retraso_max_min)}'</div><div className="k">Retraso máximo</div></div>
          </div>

          <div className="kicker">Trenes en vía</div>
          {data.trenes.map((t) => (
            <div key={t.trip_id} className="card tap" onClick={() => onNav({ name: "tren", tripId: t.trip_id, from: { name: "linea", linea } })}>
              <div className="tren-row">
                <div className="tren-hora">{t.llegada || "—:—"}<small>llegada est.</small></div>
                <div className="tren-info">
                  <div className="t1">{t.destino ? `a ${t.destino}` : "Tren en circulación"}</div>
                  <div className="t2">
                    Próxima: {t.proxima_parada}
                  </div>
                </div>
                <RetrasoPill min={t.retraso_min} />
                <span className="chev">›</span>
              </div>
            </div>
          ))}

          <div className="kicker">Estaciones con trenes aproximándose</div>
          <div className="card">
            {data.estaciones.map((e) => (
              <div key={e.stop_id} className="linea-vida" style={{ alignItems: "center" }}>
                <span className={`op-dot d-${e.nivel}`} style={{ width: 11, height: 11 }} />
                <div style={{ flex: 1 }}>
                  <b>{e.nombre}</b>
                  <div style={{ color: "var(--ink-3)", fontSize: ".8rem" }}>{e.n_trenes} {e.n_trenes === 1 ? "tren llegando" : "trenes llegando"}</div>
                </div>
                <NivelPill nivel={e.nivel} conDot={false}>
                  {e.retraso_medio_min < 2 ? "Normal" : `+${Math.round(e.retraso_medio_min)} min`}
                </NivelPill>
              </div>
            ))}
            <div style={{ color: "var(--ink-3)", fontSize: ".75rem", marginTop: 10 }}>
              Orden aproximado por secuencia de parada; el feed no publica el recorrido completo.
            </div>
          </div>
        </>
      )}
    </>
  );
}
