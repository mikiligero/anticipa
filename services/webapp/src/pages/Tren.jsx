import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { PREDICCION_VIAJERO } from "../demo/predicciones.js";
import AvisoSimulacion from "../demo/AvisoSimulacion.jsx";
import { Escala, LineaChip, NIVEL_LABEL, RetrasoPill, Vacio } from "../ui.jsx";

export default function Tren({ tripId, onBack }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let vivo = true;
    const cargar = () =>
      api.tren(tripId).then((d) => vivo && setData(d)).catch((e) => vivo && setError(e.message));
    cargar();
    const t = setInterval(cargar, 30000);
    return () => { vivo = false; clearInterval(t); };
  }, [tripId]);

  if (error)
    return (
      <>
        <button className="volver" onClick={onBack} aria-label="Volver">‹</button>
        <Vacio emoji="🚫">Ese tren ya no está en circulación o no hay datos.</Vacio>
      </>
    );
  if (!data) return <Vacio emoji="⏳">Cargando tren…</Vacio>;

  const { tren } = data;
  const prediccion = PREDICCION_VIAJERO;


  return (
    <>
      <div className="cab-detalle">
        <button className="volver" onClick={onBack} aria-label="Volver">‹</button>
        <LineaChip linea={tren.linea} />
        <h2>Tu tren, en vivo</h2>
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <b>{tren.destino ? `Destino ${tren.destino}` : "Tren en circulación"}</b>
          <span className="envivo" style={{ color: "var(--nv-normal)" }}>EN VIVO</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          <div>
            <div style={{ color: "var(--ink-3)", fontSize: ".7rem", fontWeight: 700, letterSpacing: ".5px" }}>PRÓXIMA PARADA</div>
            <div style={{ fontWeight: 800, marginTop: 4 }}>{tren.proxima_parada || "—"}</div>
          </div>
          <div>
            <div style={{ color: "var(--ink-3)", fontSize: ".7rem", fontWeight: 700, letterSpacing: ".5px" }}>LLEGADA EST.</div>
            <div className="tren-hora">{tren.llegada || "—:—"}</div>
          </div>
          <div>
            <div style={{ color: "var(--ink-3)", fontSize: ".7rem", fontWeight: 700, letterSpacing: ".5px" }}>RETRASO</div>
            <div style={{ marginTop: 4 }}><RetrasoPill min={tren.retraso_min} /></div>
          </div>
        </div>
        <div style={{ color: "var(--ink-3)", fontSize: ".75rem", marginTop: 12 }}>
          Renfe publica en el feed solo la próxima parada de cada tren; el andén no se publica.
        </div>
      </div>

      <>
          <div className="pred-hero">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 800 }}>Predicción del modelo</span>
              <span className="mini">EJEMPLO SIMULADO</span>
            </div>
            <div className="pct">{prediccion.prob_llegar_bien}%</div>
            <div style={{ opacity: 0.9 }}>prob. de terminar sin retraso grave (&lt; {prediccion.umbral_grave_min} min)</div>
            <div className="barra"><div style={{ width: `${prediccion.prob_llegar_bien}%` }} /></div>
            <div style={{ display: "flex", gap: 28 }}>
              <div>
                <div className="mini">RETRASO FINAL EST.</div>
                <div className="dato">{prediccion.retraso_final_min >= 0 ? "+" : ""}{Math.round(prediccion.retraso_final_min)} min</div>
              </div>
              <div>
                <div className="mini">CONFIANZA</div>
                <div className="dato" style={{ textTransform: "capitalize" }}>{prediccion.confianza}</div>
              </div>
            </div>
            <div className="nota">
              Valores de ejemplo para mostrar el panel; no describen el pronóstico de este tren.
            </div>
          </div>

          <AvisoSimulacion />

          <div className="card">
            <div className="kicker" style={{ margin: "0 0 8px" }}>Estado previsto del viaje · simulado</div>
            <div style={{ marginBottom: 6 }}>
              <b style={{ textTransform: "capitalize" }}>{NIVEL_LABEL[prediccion.nivel_previsto]}</b>
              <span style={{ color: "var(--ink-2)" }}> — retraso final estimado {Math.round(prediccion.retraso_final_min)} min.</span>
            </div>
            <Escala nivel={prediccion.nivel_previsto} />
          </div>
      </>
    </>
  );
}
