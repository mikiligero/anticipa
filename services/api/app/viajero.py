"""Endpoints públicos de viajero (/app/*) — consumidos por la webapp.

Sin token: exponen únicamente información derivada del Open Data (misma
filosofía que los paneles de estación). Los endpoints de operación
(/estado, /kpis...) siguen protegidos por X-API-Key.

Regla de datos del piloto: SOLO lo que viene en los feeds. No hay andén
(Renfe no lo publica) ni horario teórico por estación: "próximos trenes"
son los trenes EN CIRCULACIÓN cuya próxima parada es la estación pedida.
"""
from __future__ import annotations

import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

import main as core
from inferencia import predecir

router = APIRouter(prefix="/app", tags=["viajero"])

TZ = ZoneInfo("Europe/Madrid")

# Niveles de servicio (semáforo de 5 niveles del mockup), por retraso en min
NIVELES = [(2, "normal"), (4, "leve"), (8, "moderado"), (15, "grave")]

CAUSAS = {
    1: "Causa desconocida", 2: "Otra causa", 3: "Problema técnico", 4: "Huelga",
    5: "Manifestación", 6: "Accidente", 7: "Festivo", 8: "Meteorología", 9: "Mantenimiento",
}
EFECTOS = {
    1: "Sin servicio", 2: "Servicio reducido", 3: "Retrasos significativos",
    4: "Desvío", 5: "Servicio adicional", 6: "Servicio modificado",
    7: "Otro efecto", 8: "Efecto desconocido", 9: "Parada trasladada",
}
EFECTO_NIVEL = {1: "critico", 2: "grave", 3: "grave", 4: "moderado", 6: "moderado",
                9: "moderado", 5: "normal", 7: "leve", 8: "leve"}


def nivel_de(delay_min: float | None) -> str:
    if delay_min is None or pd.isna(delay_min):
        return "normal"
    for umbral, nombre in NIVELES:
        if delay_min < umbral:
            return nombre
    return "critico"


def _estado() -> pd.DataFrame:
    path = core.REALTIME / "estado_red.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


class _Cache:
    """Cache sencilla con TTL para consultas sobre Gold."""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._data: dict[str, tuple[float, object]] = {}

    def get(self, key: str, builder):
        hit = self._data.get(key)
        if hit and time.time() - hit[0] < self.ttl:
            return hit[1]
        value = builder()
        self._data[key] = (time.time(), value)
        return value


CACHE = _Cache()


def _nombres_lineas(nucleo: str | None = None) -> dict[str, str]:
    """Nombres asociados por itinerario al núcleo, nunca solo por código C1/C2."""
    if not nucleo:
        return {}

    def build():
        dimensiones = core.GOLD / "dim_lineas.parquet"
        itinerarios = core.GOLD / "dim_itinerarios.parquet"
        estaciones = core.DATA_ROOT / "nucleos" / "estaciones_nucleo.parquet"
        if not all(p.exists() for p in (dimensiones, itinerarios, estaciones)):
            return {}
        df = core.query_df(
            f"select n.nucleo, d.linea, mode(d.route_long_name) as nombre "
            f"from read_parquet('{dimensiones}') d "
            f"join (select distinct trip_id, lpad(trim(cast(stop_id as varchar)), 5, '0') as stop_id "
            f"from read_parquet('{itinerarios}')) i on trim(d.trip_id) = trim(i.trip_id) "
            f"join read_parquet('{estaciones}') n on i.stop_id = n.stop_id "
            "where d.linea is not null and length(trim(d.route_long_name)) > 3 "
            "group by n.nucleo, d.linea"
        )
        return {(r.nucleo, r.linea): r.nombre for r in df.itertuples()}

    nombres = CACHE.get("nombres_lineas_por_nucleo", build)
    return {linea: nombre for (n, linea), nombre in nombres.items() if n == nucleo}


def _hhmm(epoch: int | float | None) -> str | None:
    if epoch is None or pd.isna(epoch) or not epoch:
        return None
    return datetime.fromtimestamp(int(epoch), tz=TZ).strftime("%H:%M")


# ── Núcleos (catálogos de data.renfe.com → dimensión estación→núcleo) ────
def _norm_stop(s) -> str:
    s = str(s or "").strip()
    return s.zfill(5) if s.isdigit() else s


def _nucleos() -> dict[str, set[str]]:
    def build():
        p = core.DATA_ROOT / "nucleos" / "estaciones_nucleo.parquet"
        if not p.exists():
            return {}
        df = core.query_df(f"select nucleo, stop_id from read_parquet('{p}')")
        out: dict[str, set[str]] = {}
        for n, g in df.groupby("nucleo"):
            out[n] = set(g["stop_id"])
        return out

    return CACHE.get("nucleos", build)


def _nucleo_de_stop(stop_id) -> str | None:
    """Núcleo al que pertenece una estación (lookup inverso del catálogo)."""
    if not stop_id:
        return None
    s = _norm_stop(stop_id)
    for nucleo, stops in _nucleos().items():
        if s in stops:
            return nucleo
    return None


def _filtra_nucleo(df: pd.DataFrame, nucleo: str | None) -> pd.DataFrame:
    """Filtra un DataFrame con stop_id al núcleo pedido (si hay dimensión)."""
    if not nucleo or df.empty or "stop_id" not in df.columns:
        return df
    stops = _nucleos().get(nucleo)
    if not stops:
        return df
    return df[df["stop_id"].map(_norm_stop).isin(stops)]


@router.get("/nucleos")
def nucleos() -> list[str]:
    """Núcleos de Cercanías disponibles para filtrar la app."""
    return sorted(_nucleos().keys())


@router.get("/resumen")
def resumen(nucleo: str | None = Query(default=None)) -> dict:
    """Estado global de la red (o de un núcleo) para la portada de la app."""
    df = _filtra_nucleo(_estado(), nucleo)
    incidencias = _incidencias_de(nucleo)
    if df.empty:
        return {"disponible": False, "incidencias": len(incidencias), "nucleo": nucleo}
    retraso_medio = float(df["arrival_delay_min"].mean())
    en_hora_pct = float((df["arrival_delay_min"] < 5).mean() * 100)
    return {
        "disponible": True,
        "nucleo": nucleo,
        "actualizado": df["updated_at"].max(),
        "viajes_activos": int(len(df)),
        "retraso_medio_min": round(retraso_medio, 1),
        "puntualidad_pct": round(en_hora_pct),
        "nivel": nivel_de(retraso_medio),
        "incidencias": len(incidencias),
    }


@router.get("/lineas")
def lineas(nucleo: str | None = Query(default=None)) -> list[dict]:
    """Estado por línea (nivel de servicio + retraso medio actual)."""
    df = _filtra_nucleo(_estado(), nucleo)
    if df.empty or "linea" not in df.columns:
        return []
    nombres = _nombres_lineas(nucleo)
    out = []
    for linea, g in df[df["linea"].notna()].groupby("linea"):
        media = float(g["arrival_delay_min"].mean())
        out.append(
            {
                "linea": linea,
                "nombre": nombres.get(linea, f"Línea {linea}"),
                "trenes_activos": int(len(g)),
                "retraso_medio_min": round(media, 1),
                "retraso_max_min": round(float(g["arrival_delay_min"].max()), 1),
                "puntualidad_pct": round(float((g["arrival_delay_min"] < 5).mean() * 100)),
                "nivel": nivel_de(media),
            }
        )
    return sorted(out, key=lambda x: x["linea"])


def _incidencias_activas() -> list[dict]:
    def build():
        base = core.DATA_ROOT / "bronze" / "alerts"
        if not base.exists():
            return []
        fechas = sorted(d for d in base.iterdir() if d.name.startswith("date="))
        if not fechas:
            return []
        partes = sorted(fechas[-1].glob("part-*.parquet"))
        if not partes:
            return []
        df = core.query_df(f"select * from read_parquet('{partes[-1]}')")
        ahora = time.time()
        out = []
        for _, r in df.iterrows():
            if r.get("active_end") and not pd.isna(r["active_end"]) and r["active_end"] < ahora:
                continue
            lineas_afectadas = sorted(
                {
                    m.group(1)
                    for rid in str(r.get("informed_routes") or "").split(",")
                    if (m := re.search(r"([A-Z]+[0-9]+[a-z]?)\s*$", rid.strip()))
                }
            )
            efecto = int(r["effect"]) if not pd.isna(r["effect"]) else 8

            def _texto(v):  # NaN/None → None
                return v if isinstance(v, str) and v.strip() else None

            # header_text suele venir vacío en Renfe: el texto está en description_text
            descripcion = _texto(r.get("description_text"))
            titulo = _texto(r.get("header_text")) or descripcion or EFECTOS.get(efecto, "Incidencia")
            out.append(
                {
                    "id": r["entity_id"],
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "causa": CAUSAS.get(int(r["cause"]) if not pd.isna(r["cause"]) else 1),
                    "efecto": EFECTOS.get(efecto),
                    "nivel": EFECTO_NIVEL.get(efecto, "leve"),
                    "lineas": lineas_afectadas,
                    "stops": [s.strip() for s in str(r.get("informed_stops") or "").split(",") if s.strip()],
                    "desde": _hhmm(r.get("active_start")),
                    "desde_ts": None if pd.isna(r.get("active_start")) else int(r["active_start"]),
                }
            )
        return out

    # Sin cache: es un único parquet pequeño y las alertas deben ser frescas
    return build()


def _incidencias_de(nucleo: str | None) -> list[dict]:
    """Solo avisos con estaciones informadas, filtrados por el núcleo elegido."""
    data = [i for i in _incidencias_activas() if i.get("stops")]
    if not nucleo:
        return data
    stops = _nucleos().get(nucleo)
    if not stops:
        return []
    return [i for i in data if {_norm_stop(s) for s in i["stops"]} & stops]


@router.get("/incidencias")
def incidencias(nucleo: str | None = Query(default=None)) -> list[dict]:
    """Incidencias activas (feed service_alerts, último snapshot)."""
    data = _incidencias_de(nucleo)
    orden = {"critico": 0, "grave": 1, "moderado": 2, "leve": 3, "normal": 4}
    return sorted(data, key=lambda x: (orden.get(x["nivel"], 9), -(x["desde_ts"] or 0)))


@router.get("/estaciones")
def estaciones(nucleo: str | None = Query(default=None)) -> list[dict]:
    """Estaciones con trenes aproximándose ahora mismo (dato del feed)."""
    df = _filtra_nucleo(_estado(), nucleo)
    if df.empty:
        return []
    cols = ["stop_id"] + (["stop_name"] if "stop_name" in df.columns else [])
    est = df[df["stop_id"].notna()][cols].drop_duplicates()
    out = [
        {"stop_id": r["stop_id"], "nombre": r.get("stop_name") or r["stop_id"]}
        for _, r in est.iterrows()
    ]
    return sorted(out, key=lambda x: str(x["nombre"]))


@router.get("/proximos")
def proximos(
    stop_id: str | None = None,
    linea: str | None = None,
    nucleo: str | None = None,
) -> list[dict]:
    """Trenes en circulación cuya PRÓXIMA parada es la estación indicada."""
    df = _filtra_nucleo(_estado(), nucleo)
    if df.empty:
        return []
    if stop_id:
        df = df[df["stop_id"].map(_norm_stop) == _norm_stop(stop_id)]
    if linea and "linea" in df.columns:
        df = df[df["linea"] == linea]
    df = df.sort_values("arrival_time", na_position="last")
    out = []
    for _, r in df.iterrows():
        out.append(
            {
                "trip_id": r["trip_id"],
                "linea": r.get("linea"),
                "destino": _destino(r),
                "proxima_parada": r.get("stop_name") or r.get("stop_id"),
                "llegada": _hhmm(r.get("arrival_time")),
                "retraso_min": None if pd.isna(r["arrival_delay_min"]) else float(r["arrival_delay_min"]),
                "semaforo": r.get("semaforo"),
                "nivel": nivel_de(r["arrival_delay_min"]),
            }
        )
    return out



def _itinerario(trip_id: str) -> list[dict]:
    """Recorrido ordenado del viaje según stop_times (GTFS estático)."""
    p = core.GOLD / "dim_itinerarios.parquet"
    if not p.exists():
        return []
    tid = str(trip_id).replace("'", "''")
    df = core.query_df(
        f"select stop_sequence, stop_id, stop_name, hora_prog from read_parquet('{p}') "
        f"where trip_id = '{tid}' order by stop_sequence"
    )
    return df.to_dict("records")


def _hora_mas_min(hhmmss, minutos: float) -> str | None:
    """'HH:MM:SS' del GTFS (admite >24h) + minutos → 'HH:MM' local."""
    try:
        h, m, *_ = (int(x) for x in str(hhmmss).strip().split(":"))
    except (ValueError, AttributeError):
        return None
    total = h * 60 + m + round(minutos)
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _destino(r) -> str | None:
    """Destino del tren: última parada del viaje (stop_times); headsign como fallback."""
    for campo in ("destino", "trip_headsign"):
        v = r.get(campo)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None

def _predecir(df: pd.DataFrame) -> pd.DataFrame | None:
    return predecir(df, core.MODELS)


def _coords_estaciones() -> dict[str, tuple[float, float]]:
    """stop_id → (lat, lon) desde dim_estaciones (con y sin ceros a la izq.)."""
    def build():
        p = core.GOLD / "dim_estaciones.parquet"
        if not p.exists():
            return {}
        df = core.query_df(f"select stop_id, stop_lat, stop_lon from read_parquet('{p}')")
        out: dict[str, tuple[float, float]] = {}
        for r in df.itertuples():
            if pd.notna(r.stop_lat) and pd.notna(r.stop_lon):
                c = (float(r.stop_lat), float(r.stop_lon))
                out[str(r.stop_id)] = c
                out[_norm_stop(r.stop_id)] = c
        return out

    return CACHE.get("coords_estaciones", build)


def _dist2(a: tuple[float, float], b: tuple[float, float]) -> float:
    # aproximación equirectangular: suficiente a escala de núcleo
    dlat = a[0] - b[0]
    dlon = (a[1] - b[1]) * 0.75
    return dlat * dlat + dlon * dlon


def _ordenar_geo(estaciones: list[dict], inicio_stop_id: str | None = None) -> list[dict]:
    """Orden de corredor por encadenado del vecino más próximo.

    Renfe publica stop_sequence=0 en la práctica totalidad del feed, así que
    el orden se reconstruye geográficamente: desde la próxima parada del
    tren (si se indica) o desde el extremo del corredor (estación más lejana
    del centroide), saltando siempre a la estación no visitada más cercana.
    """
    coords = _coords_estaciones()

    def c(e):
        return coords.get(str(e["stop_id"])) or coords.get(_norm_stop(e["stop_id"]))

    localizadas = [e for e in estaciones if c(e)]
    resto = sorted((e for e in estaciones if not c(e)), key=lambda e: str(e["nombre"]))
    if len(localizadas) < 2:
        return localizadas + resto

    punto = None
    if inicio_stop_id:
        punto = coords.get(str(inicio_stop_id)) or coords.get(_norm_stop(inicio_stop_id))
    if punto is None:
        centro = (
            sum(c(e)[0] for e in localizadas) / len(localizadas),
            sum(c(e)[1] for e in localizadas) / len(localizadas),
        )
        punto = c(max(localizadas, key=lambda e: _dist2(c(e), centro)))

    orden, pendientes = [], localizadas[:]
    while pendientes:
        e = min(pendientes, key=lambda x: _dist2(c(x), punto))
        orden.append(e)
        pendientes.remove(e)
        punto = c(e)
    for i, e in enumerate(orden):
        e["orden"] = float(i)
    return orden + resto


def _estaciones_de_linea(df_linea: pd.DataFrame, inicio_stop_id: str | None = None) -> list[dict]:
    """Estaciones con trenes de la línea aproximándose ahora, con semáforo,
    en orden de corredor geográfico (ver _ordenar_geo)."""
    con_parada = df_linea[df_linea["stop_id"].notna()]
    if con_parada.empty:
        return []
    out = []
    for stop_id, g in con_parada.groupby("stop_id"):
        media = float(g["arrival_delay_min"].mean())
        out.append(
            {
                "stop_id": stop_id,
                "nombre": (g["stop_name"].dropna().iloc[0] if "stop_name" in g and g["stop_name"].notna().any() else stop_id),
                "n_trenes": int(len(g)),
                "retraso_medio_min": round(media, 1),
                "nivel": nivel_de(media),
            }
        )
    return _ordenar_geo(out, inicio_stop_id)


@router.get("/linea/{linea}")
def linea_detalle(linea: str, nucleo: str | None = Query(default=None)) -> dict:
    """Dashboard de línea: semáforo, trenes en vía, estaciones y predicción."""
    df = _filtra_nucleo(_estado(), nucleo)
    df = df[df["linea"] == linea] if not df.empty and "linea" in df.columns else pd.DataFrame()
    if df.empty:
        raise HTTPException(status_code=404, detail=f"Sin trenes de {linea} en circulación ahora")

    media = float(df["arrival_delay_min"].mean())
    scored = _predecir(df)

    trenes = []
    fuente = scored if scored is not None else df
    for _, r in fuente.sort_values("arrival_delay_min", ascending=False).iterrows():
        trenes.append(
            {
                "trip_id": r["trip_id"],
                "destino": _destino(r),
                "proxima_parada": r.get("stop_name") or r.get("stop_id"),
                "llegada": _hhmm(r.get("arrival_time")),
                "retraso_min": None if pd.isna(r["arrival_delay_min"]) else float(r["arrival_delay_min"]),
                "nivel": nivel_de(r["arrival_delay_min"]),
                "retraso_final_previsto_min": float(r["retraso_final_min"]) if scored is not None else None,
                "alerta": bool(r["prob_grave"] >= core.ALERT_CONFIDENCE) if scored is not None else False,
            }
        )

    prediccion = None
    if scored is not None:
        n_alertas = int((scored["prob_grave"] >= core.ALERT_CONFIDENCE).sum())
        max_pred = float(scored["retraso_final_min"].max())
        prediccion = {
            "retraso_final_medio_min": round(float(scored["retraso_final_min"].mean()), 1),
            "retraso_final_max_min": round(max_pred, 1),
            "prob_max": round(float(scored["prob_grave"].max()), 3),
            "n_alertas": n_alertas,
            "nivel_previsto": nivel_de(float(scored["retraso_final_min"].mean())),
            "mae_min": core.MODELS.meta.get("mae_min"),
        }

    nombre = _nombres_lineas(nucleo).get(linea, f"Línea {linea}")

    return {
        "linea": linea,
        "nombre": nombre,
        "nucleo": nucleo,
        "nivel": nivel_de(media),
        "retraso_medio_min": round(media, 1),
        "retraso_max_min": round(float(df["arrival_delay_min"].max()), 1),
        "puntualidad_pct": round(float((df["arrival_delay_min"] < 5).mean() * 100)),
        "trenes_activos": int(len(df)),
        "prediccion": prediccion,
        "trenes": trenes,
        "estaciones": _estaciones_de_linea(df),
    }


@router.get("/tren/{trip_id}")
def tren(trip_id: str) -> dict:
    """Detalle en vivo de un tren + predicción del modelo (si hay modelo)."""
    df = _estado()
    fila = df[df["trip_id"] == trip_id] if not df.empty else pd.DataFrame()
    if fila.empty:
        raise HTTPException(status_code=404, detail="Ese tren ya no está en circulación")
    r = fila.iloc[0]

    detalle = {
        "trip_id": trip_id,
        "linea": r.get("linea"),
        "destino": _destino(r),
        "proxima_parada": r.get("stop_name") or r.get("stop_id"),
        "stop_sequence": None if pd.isna(r.get("stop_sequence")) else int(r["stop_sequence"]),
        "llegada": _hhmm(r.get("arrival_time")),
        "retraso_min": None if pd.isna(r["arrival_delay_min"]) else float(r["arrival_delay_min"]),
        "nivel": nivel_de(r["arrival_delay_min"]),
        "actualizado": r.get("updated_at"),
    }

    prediccion = None
    proximas = []
    scored = _predecir(fila)
    if scored is not None:
        s = scored.iloc[0]
        pred = float(s["retraso_final_min"])
        prob_grave = float(s["prob_grave"])
        certeza = max(prob_grave, 1 - prob_grave)
        prediccion = {
            "retraso_final_min": round(pred, 1),
            "prob_llegar_bien": round((1 - prob_grave) * 100),
            "umbral_grave_min": core.MODELS.meta.get("alert_delay_min"),
            "confianza": "alta" if certeza >= 0.8 else "media" if certeza >= 0.6 else "baja",
            "nivel_previsto": nivel_de(pred),
            "alerta": prob_grave >= core.ALERT_CONFIDENCE,
            "modelo": {
                "mae_min": core.MODELS.meta.get("mae_min"),
                "n_train": core.MODELS.meta.get("n_train"),
                "entrenado": core.MODELS.meta.get("trained_at"),
            },
        }

        # Próximas estaciones con retraso previsto interpolado entre el
        # retraso actual y la predicción final del modelo.
        # Fuente preferente: el ITINERARIO REAL del viaje (stop_times) — las
        # estaciones que le quedan al tren tras su próxima parada, en orden.
        fuente = None
        restantes: list[dict] = []
        if not pd.isna(r["arrival_delay_min"]):
            itin = _itinerario(trip_id)
            en_itinerario = False
            if itin:
                ids = [_norm_stop(x["stop_id"]) for x in itin]
                actual_id = _norm_stop(r.get("stop_id"))
                if actual_id in ids:
                    en_itinerario = True
                    idx = ids.index(actual_id)
                    restantes = [
                        {"nombre": x["stop_name"] or x["stop_id"], "hora_prog": x.get("hora_prog")}
                        for x in itin[idx + 1:]
                    ]
                    # sin restantes = la próxima parada ES la terminal: no hay
                    # nada que listar (y el fallback mostraría estaciones ya
                    # recorridas — no debe activarse)
                    fuente = "itinerario" if restantes else "terminal"

            if not en_itinerario and not restantes and r.get("linea"):
                # Fallback (viajes de versiones GTFS antiguas): corredor
                # geográfico de la línea en el núcleo del tren
                misma_linea = df[df["linea"] == r["linea"]]
                nuc = _nucleo_de_stop(r.get("stop_id"))
                if nuc:
                    misma_linea = _filtra_nucleo(misma_linea, nuc)
                estaciones = _estaciones_de_linea(misma_linea, inicio_stop_id=r.get("stop_id"))
                restantes = [
                    {"nombre": e["nombre"]} for e in estaciones if e["stop_id"] != r.get("stop_id")
                ][:8]
                fuente = "aproximado" if restantes else None

            if restantes:
                if len(restantes) > 12:
                    # si hay que recortar, la terminal se conserva siempre
                    restantes = restantes[:11] + [restantes[-1]]
                actual = float(r["arrival_delay_min"])
                for i, e in enumerate(restantes):
                    t = (i + 1) / len(restantes)
                    previsto = actual + (pred - actual) * t
                    hora_prog = e.get("hora_prog")
                    proximas.append(
                        {
                            "nombre": e["nombre"],
                            "retraso_previsto_min": round(previsto, 1),
                            "nivel": nivel_de(previsto),
                            # hora planificada (GTFS) y prevista (planificada + retraso)
                            "hora_prog": _hora_mas_min(hora_prog, 0) if hora_prog else None,
                            "hora_prevista": _hora_mas_min(hora_prog, previsto) if hora_prog else None,
                        }
                    )

    return {
        "tren": detalle,
        "prediccion": prediccion,
        "proximas_estaciones": proximas,
        "proximas_fuente": fuente if prediccion else None,
    }
