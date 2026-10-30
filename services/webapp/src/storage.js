// Perfil local del piloto: todo en localStorage, sin backend de usuarios
// (RGPD por diseño: minimización — nada sale del navegador).
const KEY = "cercanias-app-v1";

const DEFAULTS = {
  nombre: "",
  nucleo: "Madrid", // núcleo de Cercanías sobre el que consulta la app
  estacionRef: null, // { stop_id, nombre }
  lineaRef: null,
  nivelMinimo: "moderado", // nivel mínimo de aviso
  trayectos: [], // { id, nombre, linea, origen:{stop_id,nombre}, franja, alertas:bool }
  leidas: [], // ids de alertas leídas
};

export function loadProfile() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return { ...DEFAULTS };
  }
}

export function saveProfile(profile) {
  localStorage.setItem(KEY, JSON.stringify(profile));
  return profile;
}

export const NIVEL_ORDEN = { normal: 0, leve: 1, moderado: 2, grave: 3, critico: 4 };
