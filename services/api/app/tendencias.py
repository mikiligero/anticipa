"""Tendencias reales de dos horas: una observación por viaje e intervalo."""
import logging
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import duckdb
from fastapi import HTTPException

_LOCK = threading.Lock()
_CACHE = {'at': 0, 'root': None, 'rows': []}
STEP = 300

def _files(root: Path, start: int, end: int):
    found = []
    for day in {datetime.fromtimestamp(t, ZoneInfo('Europe/Madrid')).strftime('%Y-%m-%d') for t in (start, end)}:
        for p in (root / 'bronze/trip_updates' / f'date={day}').glob('part-*.parquet'):
            # Puede haber capturas incompletas heredadas. Conservar el original,
            # omitirlo con aviso y no convertirlo en observaciones inventadas.
            try:
                with p.open('rb') as f:
                    if p.stat().st_size < 12 or f.read(4) != b'PAR1':
                        raise ValueError('Cabecera Parquet incompleta')
                    f.seek(-4, 2)
                    if f.read(4) != b'PAR1':
                        raise ValueError('Pie Parquet incompleto')
            except (OSError, ValueError):
                logging.getLogger(__name__).warning('Captura incompleta omitida: %s', p.name)
                continue
            token = p.stem[5:]
            try:
                ts = int(token) if token.isdigit() else int(datetime.strptime(token, '%Y%m%dT%H%M%SZ').replace(tzinfo=ZoneInfo('UTC')).timestamp())
            except ValueError:
                found.append(str(p))  # Un archivo compactado se filtra por sus filas.
            else:
                if start <= ts <= end:
                    found.append(str(p))
    return found

def aggregate(root: Path, start: int, end: int):
    files = _files(root, start, end)
    if not files:
        return []
    catalog = root / 'nucleos/estaciones_nucleo.parquet'
    with duckdb.connect() as con:
        con.execute("set memory_limit='256MB'")
        con.execute('set threads=1')
        return con.execute('''
            with observations as (
                select cast(floor(snapshot_ts / 300) * 300 as bigint) as bucket,
                       trim(trip_id) as trip_id, snapshot_ts,
                       lpad(trim(cast(stop_id as varchar)),5,'0') as stop_id,
                       arrival_delay / 60.0 as delay,
                       row_number() over (
                           partition by floor(snapshot_ts / 300), trim(trip_id)
                           order by snapshot_ts desc, coalesce(stop_sequence,0) desc, stop_id
                       ) as rn
                from read_parquet(?, union_by_name=true, hive_partitioning=true)
                where snapshot_ts between ? and ? and trip_id is not null
                  and length(trim(trip_id)) > 0 and arrival_delay between -300 and 7200
            ), stations as (
                select distinct nucleo, lpad(trim(cast(stop_id as varchar)),5,'0') as stop_id
                from read_parquet(?)
            )
            select bucket, nucleo, count(*) as trenes,
                   avg(delay) as media, quantile_cont(delay,0.90) as p90,
                   100.0 * count(*) filter (where delay < 5) / count(*) as puntualidad,
                   max(snapshot_ts) as ultimo_snapshot
            from observations join stations using(stop_id)
            where rn=1 group by bucket, nucleo order by bucket,nucleo
        ''', [files, start, end, str(catalog)]).fetchall()

def _save(root: Path, rows, now):
    path = root / 'tendencias/resumen.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as con:
        con.execute('''create table if not exists muestras (
            bucket integer, nucleo text, trenes integer, media real, p90 real,
            puntualidad real, ultimo_snapshot integer, primary key(bucket,nucleo))''')
        con.executemany('insert or replace into muestras values (?,?,?,?,?,?,?)', rows)
        con.execute('delete from muestras where bucket < ?', [now - 7*86400])

def tendencias(nucleo: str):
    import main as core
    from viajero import _nucleos
    if nucleo not in _nucleos():
        raise HTTPException(404, 'Núcleo desconocido')
    now = int(time.time())
    end_bucket = now // STEP * STEP
    start = end_bucket - 23 * STEP
    root = core.DATA_ROOT
    with _LOCK:
        if _CACHE['root'] != str(root) or now - _CACHE['at'] >= 60:
            rows = aggregate(root, start, now)
            _save(root, rows, now)
            _CACHE.update(at=now, root=str(root), rows=rows)
        rows = {r[0]: r for r in _CACHE['rows'] if r[1] == nucleo}
        series = []
        for bucket in range(start, end_bucket+1, STEP):
            r = rows.get(bucket)
            series.append({'ts': bucket, 'trenes': r[2] if r else 0,
                'retraso_medio_min': round(r[3],2) if r else None,
                'retraso_p90_min': round(r[4],2) if r else None,
                'puntualidad_pct': round(r[5],1) if r else None,
                'ultimo_snapshot': r[6] if r else None,
                'en_curso': bucket == end_bucket})
    return {'nucleo':nucleo, 'intervalo_min':5, 'actualizado_ts':_CACHE['at'],
            'criterio_puntualidad':'retraso < 5 min', 'serie':series}
