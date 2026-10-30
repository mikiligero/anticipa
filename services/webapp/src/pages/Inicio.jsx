import React from "react";
import { detalleIncidencia, Escala, LineaChip, NivelPill, NIVEL_LABEL, RetrasoPill, Vacio } from "../ui.jsx";

function saludo() {
  const h = new Date().getHours();
  return h < 7 ? "Buenas noches" : h < 14 ? "Buenos días" : h < 21 ? "Buenas tardes" : "Buenas noches";
}

export default function Inicio({ profile, resumen, lineas, incidencias, proximos, onNav, noLeidas }) {
  const trayecto = profile.trayectos.find((t) => t.alertas) || profile.trayectos[0];
  const lineasPersonales = new Set([
    profile.lineaRef,
    ...profile.trayectos.map((t) => t.linea),
  ].filter(Boolean));
  const mostrarTodas = !profile.lineaRef;
  const lineasVisibles = mostrarTodas
    ? lineas
    : lineas.filter((l) => lineasPersonales.has(l.linea));
  const tituloLineas = mostrarTodas
    ? "Líneas de tu núcleo"
    : lineasPersonales.size === 1 ? "Tu línea habitual" : "Tus líneas";
  const proximosRef = proximos || [];
  const proximoTren = trayecto
    ? proximosRef.find((p) => !trayecto.linea || p.linea === trayecto.linea) || proximosRef[0]
    : proximosRef[0];

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div className="appbrand">
            <img src="/logo.svg" alt="" width="42" height="42" />
            <span className="nom">
              anticipa
              <small>CERCANÍAS · RENFE</small>
            </span>
          </div>
          <div className="saludo">{saludo()}{profile.nombre ? `, ${profile.nombre}` : ""}</div>
          <h1>Tu red en directo</h1>
          {profile.nucleo && (
            <div style={{ color: "var(--magenta)", fontWeight: 700, fontSize: ".85rem", marginTop: -10, marginBottom: 14 }}>
              📍 Núcleo de {profile.nucleo}
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 10, flexShrink: 0 }}>
          <button type="button" className="volver" aria-label="Ajustes" title="Ajustes" onClick={() => onNav({ name: "ajustes" })}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="m9.5 3-.6 2.2-1.6.9-2.2-.6-2.5 4.3 1.6 1.6v1.8l-1.6 1.6 2.5 4.3 2.2-.6 1.6.9.6 2.2h5l.6-2.2 1.6-.9 2.2.6 2.5-4.3-1.6-1.6v-1.8l1.6-1.6-2.5-4.3-2.2.6-1.6-.9L14.5 3z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
          <button type="button" className="volver acceso-alertas" aria-label={noLeidas > 0 ? `Alertas: ${noLeidas} sin leer` : "Alertas"} onClick={() => onNav({ name: "alertas" })}>
            <span aria-hidden="true">🔔</span>
            {noLeidas > 0 && <span className="contador-alertas" aria-hidden="true">{noLeidas > 99 ? "99+" : noLeidas}</span>}
          </button>
        </div>
      </div>

      {trayecto && (
        <div className="hero">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span><LineaChip linea={trayecto.linea} /> <span className="sub">Tu trayecto habitual</span></span>
            <span className="envivo">EN VIVO</span>
          </div>
          <div className="ruta">{trayecto.origen?.nombre} → {trayecto.destinoLabel || trayecto.nombre}</div>
          {proximoTren ? (
            <>
              <div className="sub">PRÓXIMO TREN (aproximándose)</div>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <span className="grande">{proximoTren.llegada || "—:—"}</span>
                <RetrasoPill min={proximoTren.retraso_min} />
              </div>
              <button className="btn-blanco" onClick={() => onNav({ name: "tren", tripId: proximoTren.trip_id })}>
                Ver detalle y predicción ›
              </button>
            </>
          ) : (
            <div className="sub">Ahora mismo ningún tren se aproxima a {trayecto.origen?.nombre}.</div>
          )}
        </div>
      )}

      {resumen?.disponible && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: 800, fontSize: ".8rem", letterSpacing: ".6px", color: "var(--ink-2)" }}>🚦 ESTADO DE LA RED</span>
            <NivelPill nivel={resumen.nivel} conDot={false} />
          </div>
          <Escala nivel={resumen.nivel} />
          <div style={{ color: "var(--ink-2)", fontSize: ".88rem", marginTop: 10 }}>
            {resumen.viajes_activos} trenes en circulación · retraso medio {resumen.retraso_medio_min} min ·
            nivel {NIVEL_LABEL[resumen.nivel].toLowerCase()} ahora mismo.
          </div>
        </div>
      )}

      {resumen?.disponible && (
        <div className="tiles">
          <div className="tile">
            <div className={`v ${resumen.puntualidad_pct >= 80 ? "ok" : resumen.puntualidad_pct >= 60 ? "warn" : "bad"}`}>{resumen.puntualidad_pct}%</div>
            <div className="k">En hora ahora</div>
          </div>
          <div className="tile">
            <div className={`v ${resumen.retraso_medio_min < 4 ? "ok" : resumen.retraso_medio_min < 8 ? "warn" : "bad"}`}>+{resumen.retraso_medio_min}'</div>
            <div className="k">Retraso medio</div>
          </div>
          <div className="tile">
            <div className={`v ${resumen.incidencias === 0 ? "ok" : "bad"}`}>{resumen.incidencias}</div>
            <div className="k">Incidencias</div>
          </div>
        </div>
      )}

      <div className="kicker">
        Próximos trenes {profile.estacionRef ? `· ${profile.estacionRef.nombre}` : ""}
        <a href="#" onClick={(e) => { e.preventDefault(); onNav({ name: "ajustes" }); }}>Cambiar estación →</a>
      </div>
      {!profile.estacionRef && (
        <Vacio emoji="📍">Elige tu <b>estación de referencia</b> en Ajustes para ver los trenes que se aproximan.</Vacio>
      )}
      {profile.estacionRef && proximosRef.length === 0 && (
        <Vacio emoji="🌙">Ningún tren se aproxima ahora mismo a {profile.estacionRef.nombre}.</Vacio>
      )}
      {proximosRef.slice(0, 6).map((p) => (
        <div key={p.trip_id} className="card tap" onClick={() => onNav({ name: "tren", tripId: p.trip_id })}>
          <div className="tren-row">
            <div className="tren-hora">{p.llegada || "—:—"}<small>llegada est.</small></div>
            <div className="tren-info">
              <div className="t1"><LineaChip linea={p.linea} /> {p.destino ? ` a ${p.destino}` : ""}</div>
              <div className="t2">Próxima parada: {p.proxima_parada}</div>
            </div>
            <RetrasoPill min={p.retraso_min} />
            <span className="chev">›</span>
          </div>
        </div>
      ))}

      <div className="kicker">{tituloLineas}</div>
      {!mostrarTodas && lineasVisibles.length === 0 && (
        <Vacio emoji="🚆">Ahora mismo no hay trenes en circulación de tus líneas en este núcleo.</Vacio>
      )}
      {lineasVisibles.map((l) => (
        <div key={l.linea} className="card tap" onClick={() => onNav({ name: "linea", linea: l.linea })}>
          <div className="tren-row">
            <LineaChip linea={l.linea} />
            <div className="tren-info">
              <div className="t1">{l.nombre || `Línea ${l.linea}`}</div>
              <div className="t2">{l.trenes_activos} trenes · retraso medio {l.retraso_medio_min} min</div>
            </div>
            <NivelPill nivel={l.nivel} />
            <span className="chev">›</span>
          </div>
        </div>
      ))}

      <div className="kicker">Incidencias activas</div>
      {incidencias.length === 0 && <Vacio emoji="✅">Sin incidencias activas en la red.</Vacio>}
      {incidencias.map((i) => (
        <div key={i.id} className={`card alerta b-${i.nivel}`}>
          <div className="meta">
            {i.lineas.map((l) => <LineaChip key={l} linea={l} />)}
            <NivelPill nivel={i.nivel} conDot={false} />
            {i.desde && <span className="cuando">Desde {i.desde}</span>}
          </div>
          <div className="titulo">{i.titulo}</div>
          {detalleIncidencia(i) && <div className="detalle">{detalleIncidencia(i)}</div>}
        </div>
      ))}

      <div className="footer-nota">Plataforma de Monitorización · Red de Cercanías<br />Datos: Renfe Open Data (GTFS-Realtime)</div>
    </>
  );
}
