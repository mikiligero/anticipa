"""Mapa del operador: trazados por núcleo y posiciones recientes, sin simulación."""
import json
import math
import time
from functools import lru_cache
from pathlib import Path
import pandas as pd
from fastapi import HTTPException

@lru_cache(maxsize=4)
def _read_network(path: str, mtime: int) -> dict:
    return json.loads(Path(path).read_text())

def red(nucleo: str) -> dict:
    import main as core
    path = core.DATA_ROOT / 'mapa/redes.json'
    if not path.exists():
        raise HTTPException(503, 'Los trazados aún no están disponibles')
    networks = _read_network(str(path), path.stat().st_mtime_ns)
    if nucleo not in networks:
        raise HTTPException(404, 'Núcleo desconocido')
    return networks[nucleo]

def trenes(nucleo: str) -> dict:
    import main as core
    from viajero import _nucleos, _norm_stop, nivel_de
    stations = _nucleos().get(nucleo)
    if not stations:
        raise HTTPException(404, 'Núcleo desconocido')
    now = time.time()
    result = {'nucleo': nucleo, 'consultado_ts': int(now), 'trenes': []}
    vp_path = core.REALTIME / 'posiciones.parquet'
    if not vp_path.exists():
        return result
    vp = pd.read_parquet(vp_path)
    vp = vp[vp['snapshot_ts'].between(now - 300, now + 60)].copy()
    vp = vp.dropna(subset=['trip_id', 'latitude', 'longitude'])
    vp = vp[vp.latitude.between(-90, 90) & vp.longitude.between(-180, 180) & ~((vp.latitude == 0) & (vp.longitude == 0))]
    vp['trip_id'] = vp.trip_id.str.strip()
    state_path = core.REALTIME / 'estado_red.parquet'
    if state_path.exists():
        state = pd.read_parquet(state_path)
        state = state[state.snapshot_ts.between(now - 300, now + 60)].dropna(subset=['trip_id']).copy()
        state['trip_id'] = state.trip_id.str.strip()
        cols = [c for c in ['trip_id', 'linea', 'stop_id', 'stop_name', 'arrival_delay_min'] if c in state]
        state = state.sort_values('snapshot_ts').drop_duplicates('trip_id', keep='last')
        vp = vp.merge(state[cols].rename(columns={'stop_id': 'next_stop_id'}), on='trip_id', how='left')
    def value(row, key):
        v = row.get(key)
        return None if v is None or pd.isna(v) else v
    for _, r in vp.iterrows():
        stop = value(r, 'stop_id') or value(r, 'next_stop_id')
        if stop is None or _norm_stop(stop) not in stations:
            continue
        delay = value(r, 'arrival_delay_min')
        delay = float(delay) if delay is not None and math.isfinite(float(delay)) else None
        result['trenes'].append({
            'id': str(value(r, 'vehicle_id') or r.trip_id),
            'linea': value(r, 'linea_label') or value(r, 'linea'),
            'lat': float(r.latitude), 'lon': float(r.longitude),
            'stop_id': _norm_stop(stop), 'proxima_parada': value(r, 'stop_name'),
            'retraso_min': delay, 'nivel': nivel_de(delay) if delay is not None else 'sin_dato',
            'snapshot_ts': int(r.snapshot_ts),
        })
    return result
