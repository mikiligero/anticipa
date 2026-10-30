import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../api.js";
import "./mapa.css";

const COLORES = { normal: "#0a7d33", leve: "#c98500", moderado: "#d95f16", grave: "#cf2f2f", critico: "#26262b", sin_dato: "#6b7280" };
const text = (value) => { const el = document.createElement("span"); el.textContent = value; return el; };

export default function MapaRed({ nucleo }) {
  const [abierto, setAbierto] = useState(false);
  if (abierto) return <MapaContenido nucleo={nucleo} onClose={() => setAbierto(false)} />;
  return (
    <section className="card mapa-panel mapa-plegado" aria-label={`Mapa ferroviario de ${nucleo}`}>
      <div className="mapa-cabecera">
        <div><h2>Mapa de la red · {nucleo}</h2><p>Trazados y posiciones de los trenes de este núcleo.</p></div>
        <button type="button" className="op-btn" aria-expanded={false} onClick={() => setAbierto(true)}>Mostrar mapa ▾</button>
      </div>
    </section>
  );
}

function MapaContenido({ nucleo, onClose }) {
  const container = useRef(null);
  const map = useRef(null);
  const layers = useRef({});
  const centered = useRef(false);
  const [red, setRed] = useState(null);
  const [trenes, setTrenes] = useState([]);
  const [errorRed, setErrorRed] = useState("");
  const [errorTrenes, setErrorTrenes] = useState("");
  const [actualizado, setActualizado] = useState(null);
  const [linea, setLinea] = useState("");
  const [ampliado, setAmpliado] = useState(false);
  const [fondoError, setFondoError] = useState(false);

  useEffect(() => {
    const m = L.map(container.current, { scrollWheelZoom: false, zoomAnimation: false, fadeAnimation: false, markerZoomAnimation: false }).setView([40.4, -3.7], 6);
    map.current = m;
    const base = L.tileLayer(import.meta.env.VITE_MAP_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(m);
    base.on("tileerror", () => setFondoError(true));
    m.createPane("stations"); m.getPane("stations").style.zIndex = 420;
    m.createPane("trains"); m.getPane("trains").style.zIndex = 450;
    layers.current = { tracks: L.layerGroup().addTo(m), stations: L.layerGroup().addTo(m), trains: L.layerGroup().addTo(m) };
    const observer = new ResizeObserver(() => m.invalidateSize({ animate: false, pan: false }));
    observer.observe(container.current);
    return () => { observer.disconnect(); m.remove(); map.current = null; };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    api.mapaRed(nucleo, controller.signal).then((r) => {
      if (r.nucleo !== nucleo) throw new Error("Núcleo inesperado");
      setRed(r);
    }).catch((e) => { if (e.name !== "AbortError") setErrorRed("No se pudieron cargar los trazados de este núcleo."); });
    return () => controller.abort();
  }, [nucleo]);

  useEffect(() => {
    const controller = new AbortController();
    let timer;
    const load = async () => {
      try {
        const r = await api.mapaTrenes(nucleo, controller.signal);
        if (controller.signal.aborted) return;
        if (r.nucleo !== nucleo) throw new Error("Núcleo inesperado");
        setTrenes(r.trenes); setActualizado(r.consultado_ts); setErrorTrenes("");
      } catch (e) {
        if (controller.signal.aborted) return;
        setTrenes([]); setErrorTrenes("Posiciones no disponibles. Reintentando…");
      }
      if (!controller.signal.aborted) timer = setTimeout(load, 30000);
    };
    load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [nucleo]);

  useEffect(() => {
    const close = (e) => { if (e.key === "Escape") setAmpliado(false); };
    if (ampliado) window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [ampliado]);

  const features = red?.trazados?.features || [];
  const lineas = [...new Set(features.flatMap((f) => f.properties.lineas))].sort();
  const visibles = trenes.filter((t) => !linea || t.linea === linea);

  useEffect(() => {
    if (!red || !map.current) return;
    const { tracks, stations } = layers.current;
    tracks.clearLayers(); stations.clearLayers();
    const filtered = features.filter((f) => !linea || f.properties.lineas.includes(linea));
    const geo = L.geoJSON({ type: "FeatureCollection", features: filtered }, {
      style: (f) => ({ color: f.properties.colores[linea || f.properties.lineas[0]] || "#8a0a5a", weight: 4, opacity: 0.65 }),
      onEachFeature: (f, layer) => layer.bindTooltip(text(`${f.properties.lineas.join(" · ")} · ${nucleo}`)),
    }).addTo(tracks);
    for (const s of red.estaciones) {
      L.circleMarker([s.lat, s.lon], { pane: "stations", radius: 3, color: "#475569", weight: 1, fillColor: "#fff", fillOpacity: 1 })
        .bindTooltip(text(s.nombre)).addTo(stations);
    }
    if (!centered.current) {
      let bounds = geo.getBounds();
      if (!bounds.isValid() && red.estaciones.length) bounds = L.latLngBounds(red.estaciones.map((s) => [s.lat, s.lon]));
      if (bounds.isValid()) { map.current.fitBounds(bounds, { padding: [24, 24], maxZoom: 12, animate: false }); centered.current = true; }
    }
  }, [red, linea]);

  useEffect(() => {
    if (!map.current) return;
    const layer = layers.current.trains; layer.clearLayers();
    for (const t of visibles) {
      const popup = document.createElement("div");
      const title = document.createElement("strong"); title.textContent = t.linea ? `Línea ${t.linea}` : "Tren en circulación"; popup.append(title);
      const lines = [t.proxima_parada && `Próxima parada: ${t.proxima_parada}`,
        t.retraso_min == null ? "Retraso sin dato" : t.retraso_min < 2 ? "En hora" : `Retraso: +${Math.round(t.retraso_min)} min`,
        `Posición: ${new Date(t.snapshot_ts * 1000).toLocaleTimeString("es-ES")}`].filter(Boolean);
      for (const line of lines) { const p = document.createElement("div"); p.textContent = line; popup.append(p); }
      L.circleMarker([t.lat, t.lon], { pane: "trains", radius: 8, color: "#fff", weight: 2, fillColor: COLORES[t.nivel] || COLORES.sin_dato, fillOpacity: 1 })
        .bindPopup(popup).bindTooltip(text(t.linea || "Tren"), { direction: "top" }).addTo(layer);
    }
  }, [trenes, linea]);

  const centrar = () => {
    if (!map.current || !red) return;
    const coords = features.flatMap((f) => f.geometry.coordinates.map(([lon, lat]) => [lat, lon]));
    if (coords.length) map.current.fitBounds(L.latLngBounds(coords), { padding: [24, 24], animate: false });
  };

  return (
    <section className={`card mapa-panel ${ampliado ? "mapa-ampliado" : ""}`} aria-label={`Mapa ferroviario de ${nucleo}`}>
      <div className="mapa-cabecera">
        <div><h2>Mapa de la red · {nucleo}</h2><p>{visibles.length} trenes con posición reciente{actualizado ? ` · actualizado ${new Date(actualizado * 1000).toLocaleTimeString("es-ES")}` : ""}</p></div>
        <div className="mapa-controles">
          <label>Línea <select value={linea} onChange={(e) => setLinea(e.target.value)}><option value="">Todas</option>{lineas.map((l) => <option key={l}>{l}</option>)}</select></label>
          <button type="button" className="op-btn" onClick={centrar}>Centrar núcleo</button>
          <button type="button" className="op-btn" aria-expanded={ampliado} onClick={() => setAmpliado((v) => !v)}>{ampliado ? "Reducir mapa" : "Ampliar mapa"}</button>
          <button type="button" className="op-btn" aria-expanded={true} onClick={onClose}>Ocultar mapa ▴</button>
        </div>
      </div>
      <div className="mapa-contenedor" ref={container} />
      <div className="mapa-leyenda">
        <span><i className="mapa-trazado" />Trazados Renfe</span><span><i className="mapa-estacion" />Estaciones</span>
        {[["normal", "En hora"], ["leve", "2–4 min"], ["moderado", "4–8 min"], ["grave", "8–15 min"], ["critico", "≥15 min"], ["sin_dato", "Sin dato"]].map(([key, label]) => <span key={key}><i style={{ background: COLORES[key] }} />{label}</span>)}
      </div>
      <p className="mapa-nota" role="status">{errorRed || (!red ? "Cargando trazados…" : !features.length ? "Este núcleo no tiene trazados disponibles." : "")}{errorTrenes ? ` ${errorTrenes}` : actualizado && !visibles.length ? " No hay posiciones recientes para esta selección." : ""}{fondoError ? " El fondo cartográfico no está disponible; se mantienen los trazados y trenes." : ""}</p>
      <p className="mapa-nota">Posiciones reales · actualización cada 30 s · se ocultan las de más de 5 min. Trazados GTFS del {red?.fecha_trazados || "—"}.</p>
    </section>
  );
}
