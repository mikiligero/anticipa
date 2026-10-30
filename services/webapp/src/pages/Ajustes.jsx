import React, { useEffect, useState } from "react";

const NIVELES_AVISO = [
  ["leve", "Leve o superior"],
  ["moderado", "Moderado o superior"],
  ["grave", "Solo grave y crítico"],
];

export default function Ajustes({ profile, setProfile, estaciones, lineas, nucleos, onSaved }) {
  const [errorGuardado, setErrorGuardado] = useState("");
  useEffect(() => {
    setErrorGuardado("");
  }, [profile]);

  const guardar = () => {
    try {
      setProfile(profile);
      setErrorGuardado("");
      onSaved?.();
    } catch {
        setErrorGuardado("No se pudieron guardar los ajustes. Comprueba que el navegador permite almacenar datos.");
    }
  };

  const iniciales = (profile.nombre || "Viajero A")
    .split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

  return (
    <>
      <div className="saludo">Tu cuenta</div>
      <h1>Ajustes</h1>

      <div className="card" style={{ display: "flex", gap: 14, alignItems: "center" }}>
        <div className="avatar">{iniciales}</div>
        <div style={{ flex: 1 }}>
          <input
            style={{ border: 0, fontSize: "1.1rem", fontWeight: 800, width: "100%", outline: "none", background: "transparent", color: "var(--ink)" }}
            value={profile.nombre}
            placeholder="Tu nombre"
            onChange={(e) => setProfile({ ...profile, nombre: e.target.value })}
          />
          <div style={{ color: "var(--ink-2)", fontSize: ".85rem" }}>
            Viajero/a habitual{profile.lineaRef ? ` · ${profile.lineaRef}` : ""}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="fila-ajuste">
          <span className="k">Núcleo</span>
          <select
            style={{ border: 0, background: "transparent", color: "var(--magenta)", fontWeight: 700, fontSize: "1rem", textAlign: "right" }}
            value={profile.nucleo || "Madrid"}
            onChange={(e) =>
              // al cambiar de núcleo, la estación y línea de referencia dejan de aplicar
              setProfile({ ...profile, nucleo: e.target.value, estacionRef: null, lineaRef: null })
            }
          >
            {(nucleos.length ? nucleos : ["Madrid"]).map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        <div className="fila-ajuste">
          <span className="k">Estación de referencia</span>
          <select
            style={{ border: 0, background: "transparent", color: "var(--ink-2)", fontSize: "1rem", textAlign: "right", maxWidth: "55%" }}
            value={profile.estacionRef?.stop_id || ""}
            onChange={(e) => {
              const est = estaciones.find((x) => x.stop_id === e.target.value) || null;
              setProfile({ ...profile, estacionRef: est });
            }}
          >
            <option value="">— Elegir —</option>
            {profile.estacionRef && !estaciones.some((x) => x.stop_id === profile.estacionRef.stop_id) && (
              <option value={profile.estacionRef.stop_id}>{profile.estacionRef.nombre}</option>
            )}
            {estaciones.map((e) => (
              <option key={e.stop_id} value={e.stop_id}>{e.nombre}</option>
            ))}
          </select>
        </div>
        <div className="fila-ajuste">
          <span className="k">Línea habitual</span>
          <select
            style={{ border: 0, background: "transparent", color: "var(--ink-2)", fontSize: "1rem", textAlign: "right" }}
            value={profile.lineaRef || ""}
            onChange={(e) => setProfile({ ...profile, lineaRef: e.target.value || null })}
          >
            <option value="">Todas</option>
            {lineas.map((l) => <option key={l.linea} value={l.linea}>{l.linea}</option>)}
          </select>
        </div>
        <div className="fila-ajuste">
          <span className="k">Nivel mínimo de aviso</span>
          <select
            style={{ border: 0, background: "transparent", color: "var(--nv-moderado)", fontWeight: 700, fontSize: "1rem", textAlign: "right" }}
            value={profile.nivelMinimo}
            onChange={(e) => setProfile({ ...profile, nivelMinimo: e.target.value })}
          >
            {NIVELES_AVISO.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="fila-ajuste">
          <span className="k">Idioma</span>
          <span className="v">Español</span>
        </div>
      </div>

      <button type="button" className="btn primario" onClick={guardar}>
        Guardar ajustes
      </button>
      <div role="status" aria-live="polite" style={{ marginTop: 10, textAlign: "center", fontSize: ".88rem", color: errorGuardado ? "var(--nv-grave)" : "var(--ink-2)" }}>
        {errorGuardado}
      </div>

      <div className="footer-nota">
        <img src="/logo.svg" alt="Anticipa" width="52" height="52" />
      </div>
    </>
  );
}
