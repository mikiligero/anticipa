import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import { loadProfile, saveProfile, NIVEL_ORDEN } from "./storage.js";
import Ajustes from "./pages/Ajustes.jsx";
import Alertas from "./pages/Alertas.jsx";
import Inicio from "./pages/Inicio.jsx";
import Linea from "./pages/Linea.jsx";
import Operador from "./pages/Operador.jsx";
import Trayectos from "./pages/Trayectos.jsx";
import Tren from "./pages/Tren.jsx";

const POLL_MS = 30000;

export default function App() {
  // /operador → Centro de Control (desktop); el resto → app móvil de viajero
  if (window.location.pathname.startsWith("/operador")) {
    return <Operador />;
  }
  return <AppViajero />;
}

function AppViajero() {
  const [profile, setProfileState] = useState(loadProfile);
  const [view, setView] = useState({ name: "inicio" });
  const [resumen, setResumen] = useState(null);
  const [lineas, setLineas] = useState([]);
  const [incidencias, setIncidencias] = useState([]);
  const [estaciones, setEstaciones] = useState([]);
  const [proximos, setProximos] = useState([]);
  const [nucleos, setNucleos] = useState([]);

  const setProfile = useCallback((p) => setProfileState(saveProfile(p)), []);

  useEffect(() => {
    api.nucleos().then(setNucleos).catch(() => {});
  }, []);

  useEffect(() => {
    let vivo = true;
    const nucleo = profile.nucleo || null;
    const cargar = async () => {
      try {
        const [r, l, i, e] = await Promise.all([
          api.resumen(nucleo), api.lineas(nucleo), api.incidencias(nucleo), api.estaciones(nucleo),
        ]);
        if (!vivo) return;
        setResumen(r); setLineas(l); setIncidencias(i); setEstaciones(e);
        if (profile.estacionRef) {
          setProximos(await api.proximos(profile.estacionRef.stop_id, nucleo));
        } else {
          setProximos([]);
        }
      } catch {
        /* la API puede estar arrancando: se reintenta en el siguiente ciclo */
      }
    };
    cargar();
    const t = setInterval(cargar, POLL_MS);
    return () => { vivo = false; clearInterval(t); };
  }, [profile.estacionRef?.stop_id, profile.nucleo]);

  // ── Feed de alertas: incidencias del feed + retrasos en tus trayectos ──
  const alertas = useMemo(() => {
    const minimo = NIVEL_ORDEN[profile.nivelMinimo] ?? 2;
    const out = [];

    for (const p of proximos) {
      if (p.retraso_min != null && p.retraso_min >= 5) {
        out.push({
          id: `tren-${p.trip_id}`,
          nivel: p.nivel,
          titulo: `Tu tren de las ${p.llegada || "—"} llega con +${Math.round(p.retraso_min)} min`,
          detalle: `${p.linea || ""} · próxima parada ${p.proxima_parada}`,
          desde_ts: Math.floor(Date.now() / 1000),
          lineas: p.linea ? [p.linea] : [],
        });
      }
    }

    for (const t of profile.trayectos.filter((x) => x.alertas && x.linea)) {
      const l = lineas.find((x) => x.linea === t.linea);
      if (l && NIVEL_ORDEN[l.nivel] >= 2) {
        out.push({
          id: `linea-${l.linea}-${l.nivel}`,
          nivel: l.nivel,
          titulo: `Retrasos en ${l.linea}: +${l.retraso_medio_min} min de media`,
          detalle: `Afecta a tu trayecto "${t.nombre}"`,
          consejo: l.nivel === "moderado",
          desde_ts: Math.floor(Date.now() / 1000),
          lineas: [l.linea],
        });
      }
    }

    for (const i of incidencias) {
      if ((NIVEL_ORDEN[i.nivel] ?? 0) >= minimo) out.push(i);
    }

    const vistos = new Set();
    return out.filter((a) => !vistos.has(a.id) && vistos.add(a.id));
  }, [incidencias, proximos, lineas, profile.trayectos, profile.nivelMinimo]);

  const noLeidas = alertas.filter((a) => !profile.leidas.includes(a.id)).length;
  const marcarLeidas = (ids) =>
    setProfile({ ...profile, leidas: [...new Set([...profile.leidas, ...ids])].slice(-300) });

  const onNav = (v) => setView(v);

  return (
    <div className="phone">
      <div className="content">
        {view.name === "inicio" && (
          <Inicio {...{ profile, resumen, lineas, incidencias, proximos, onNav, noLeidas }} />
        )}
        {view.name === "trayectos" && (
          <Trayectos {...{ profile, setProfile, lineas, estaciones }} />
        )}
        {view.name === "alertas" && (
          <Alertas alertas={alertas} leidas={profile.leidas} marcarLeidas={marcarLeidas} />
        )}
        {view.name === "ajustes" && (
          <Ajustes {...{ profile, setProfile, estaciones, lineas, nucleos }} onSaved={() => onNav({ name: "inicio" })} />
        )}
        {view.name === "linea" && (
          <Linea
            linea={view.linea}
            nucleo={profile.nucleo}
            lineas={lineas}
            onNav={onNav}
            onBack={() => setView({ name: "inicio" })}
          />
        )}
        {view.name === "tren" && (
          <Tren tripId={view.tripId} onBack={() => setView(view.from || { name: "inicio" })} />
        )}
      </div>

      <nav className="tabbar">
        {[
          ["inicio", "⌂", "Inicio"],
          ["trayectos", "⤳", "Trayectos"],
          ["alertas", "🔔", "Alertas"],
          ["ajustes", "⚙", "Ajustes"],
        ].map(([name, ico, label]) => (
          <button key={name} className={view.name === name ? "on" : ""} onClick={() => setView({ name })}>
            <span className="ico" aria-hidden="true">{ico}</span>
            {label}
            {name === "alertas" && noLeidas > 0 && <span className="badge">{noLeidas}</span>}
          </button>
        ))}
      </nav>
    </div>
  );
}
