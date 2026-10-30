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

  const { tren, prediccion: prediccionReal, proximas_estaciones: proximas = [], proximas_fuente: fuente } = data;
  const simulada = !prediccionReal;
  const prediccion = prediccionReal || PREDICCION_VIAJERO;


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
              <span className="mini">{simulada ? "EJEMPLO SIMULADO" : "GTFS-RT + histórico propio"}</span>
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
              {simulada ? "Valores de ejemplo para mostrar el panel; no describen el pronóstico de este tren." : (
                <>Modelo entrenado con {prediccion.modelo?.n_train?.toLocaleString("es")} observaciones ·
                MAE {prediccion.modelo?.mae_min} min · las predicciones son probabilísticas.</>
              )}
            </div>
          </div>

          {simulada && <AvisoSimulacion />}

          <div className="card">
            <div className="kicker" style={{ margin: "0 0 8px" }}>Estado previsto del viaje{simulada ? " · simulado" : ""}</div>
            <div style={{ marginBottom: 6 }}>
              <b style={{ textTransform: "capitalize" }}>{NIVEL_LABEL[prediccion.nivel_previsto]}</b>
              <span style={{ color: "var(--ink-2)" }}> — retraso final estimado {Math.round(prediccion.retraso_final_min)} min.</span>
            </div>
            <Escala nivel={prediccion.nivel_previsto} />
          </div>

          {fuente === "terminal" && (
            <div className="card" style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: "1.4rem" }} aria-hidden="true">🏁</span>
              <div>
                <b>Llegando a su destino</b>
                <div style={{ color: "var(--ink-2)", fontSize: ".9rem" }}>
                  {tren.proxima_parada} es la última parada del viaje.
                </div>
              </div>
            </div>
          )}

          {proximas.length > 0 && (
            <>
              <div className="kicker">Retraso previsto por estación</div>
              <div className="card">
                {proximas.map((e, idx) => (
                  <div key={`${e.nombre}-${idx}`} className="linea-vida" style={{ alignItems: "center" }}>
                    <span className={`op-dot d-${e.nivel}`} style={{ width: 11, height: 11 }} />
                    <div style={{ flex: 1 }}>
                      <b>{e.nombre}</b>
                      {e.hora_prog && (
                        <div style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: ".85rem", marginTop: 2 }}>
                          <span style={{ color: "var(--ink-3)", textDecoration: "line-through" }}>{e.hora_prog}</span>
                          <span style={{ color: "var(--ink-3)" }}> → </span>
                          <b>{e.hora_prevista}</b>
                        </div>
                      )}
                    </div>
                    <span style={{ fontFamily: "ui-monospace, Menlo, monospace", fontWeight: 700, color: e.nivel === "normal" ? "var(--nv-normal)" : e.nivel === "leve" ? "var(--nv-leve)" : e.nivel === "moderado" ? "var(--nv-moderado)" : "var(--nv-grave)" }}>
                      +{Math.round(e.retraso_previsto_min)} min
                    </span>
                  </div>
                ))}
                <div style={{ color: "var(--ink-3)", fontSize: ".75rem", marginTop: 10 }}>
                  {fuente === "itinerario"
                    ? "Estaciones restantes del itinerario real del viaje (GTFS); retraso interpolado entre el actual y la predicción final del modelo."
                    : "Estimación aproximada por corredor de la línea (viaje sin itinerario en el GTFS vigente); retraso interpolado entre el actual y la predicción final."}
                </div>
              </div>
            </>
          )}
      </>
    </>
  );
}
