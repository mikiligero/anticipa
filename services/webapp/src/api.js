// Cliente de la API pública de viajero (/app/*), proxyada por nginx en /api
const BASE = "/api/app";

async function getJSON(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

const q = (params) => {
  const s = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v != null && v !== "")
  ).toString();
  return s ? `?${s}` : "";
};

async function getOpJSON(path, signal) {
  // /api-op: nginx inyecta el token de operación (no viaja en el cliente)
  const res = await fetch(`/api-op${path}`, { signal });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export const api = {
  tendencias: (nucleo, signal) => getOpJSON(`/tendencias${q({ nucleo })}`, signal),
  mapaRed: (nucleo, signal) => getOpJSON(`/mapa/red${q({ nucleo })}`, signal),
  mapaTrenes: (nucleo, signal) => getOpJSON(`/mapa/trenes${q({ nucleo })}`, signal),
  prediccionRed: (nucleo) => getOpJSON(`/prediccion${q({ nucleo })}`),
  nucleos: () => getJSON("/nucleos"),
  resumen: (nucleo) => getJSON(`/resumen${q({ nucleo })}`),
  lineas: (nucleo) => getJSON(`/lineas${q({ nucleo })}`),
  incidencias: (nucleo) => getJSON(`/incidencias${q({ nucleo })}`),
  estaciones: (nucleo) => getJSON(`/estaciones${q({ nucleo })}`),
  proximos: (stopId, nucleo, linea) => getJSON(`/proximos${q({ stop_id: stopId, nucleo, linea })}`),
  linea: (linea, nucleo) => getJSON(`/linea/${encodeURIComponent(linea)}${q({ nucleo })}`),
  tren: (tripId) => getJSON(`/tren/${encodeURIComponent(tripId)}`),
};
