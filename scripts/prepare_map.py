"""Construye el mapa por núcleo a partir de un ZIP GTFS y el catálogo de estaciones."""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import zipfile
from collections import defaultdict
from pathlib import Path
import duckdb


def rows(file):
    return ({k.strip(): (v or '').strip() for k, v in r.items()} for r in csv.DictReader(file))


def prepare(data_root: Path, archive: Path, version: str):
    with duckdb.connect() as con:
        catalog = con.execute('select nucleo, stop_id from read_parquet(?)', [str(data_root / 'nucleos/estaciones_nucleo.parquet')]).fetchall()
    station_nuclei = defaultdict(set)
    for n, s in catalog:
        station_nuclei[str(s).strip().zfill(5)].add(n)
    with zipfile.ZipFile(archive) as z:
        def read(name):
            return io.TextIOWrapper(z.open(name), encoding='utf-8-sig')
        with read('trips.txt') as f:
            trips = list(rows(f))
        with read('routes.txt') as f:
            routes = {r['route_id']: r for r in rows(f)}
        with read('stops.txt') as f:
            stops = list(rows(f))
        points = defaultdict(dict)
        with read('shapes.txt') as f:
            for r in rows(f):
                lat, lon = float(r['shape_pt_lat']), float(r['shape_pt_lon'])
                seq = int(r['shape_pt_sequence'])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError('Coordenada de trazado inválida')
                if seq in points[r['shape_id']]:
                    raise ValueError('Secuencia duplicada en un trazado')
                points[r['shape_id']][seq] = [lon, lat]
        trip_shapes = {r['trip_id']: r['shape_id'] for r in trips if r.get('shape_id')}
        unknown = set(trip_shapes.values()) - points.keys()
        if unknown:
            raise ValueError('Hay viajes que referencian trazados ausentes')
        shape_nuclei = defaultdict(set)
        with read('stop_times.txt') as f:
            for r in rows(f):
                shape = trip_shapes.get(r['trip_id'])
                if shape:
                    shape_nuclei[shape].update(station_nuclei.get(r['stop_id'].zfill(5), set()))
    shape_routes = defaultdict(set)
    for r in trips:
        if r.get('shape_id'):
            shape_routes[r['shape_id']].add(r['route_id'])
    result = {}
    for n in sorted({n for n, _ in catalog}):
        features = []
        for sid, coords in points.items():
            if n not in shape_nuclei[sid] or len(coords) < 2:
                continue
            associated = [routes[rid] for rid in sorted(shape_routes[sid])]
            lines = sorted({r['route_short_name'] for r in associated if r['route_short_name']})
            colors = {r['route_short_name']: '#' + r['route_color'] for r in associated if r.get('route_color')}
            features.append({'type': 'Feature', 'geometry': {'type':'LineString','coordinates':[c for _, c in sorted(coords.items())]}, 'properties': {'shape_id':sid,'lineas':lines,'colores':colors}})
        stations = [{'stop_id':s['stop_id'].zfill(5),'nombre':s['stop_name'],'lat':float(s['stop_lat']),'lon':float(s['stop_lon'])} for s in stops if n in station_nuclei.get(s['stop_id'].zfill(5), set()) and s.get('stop_lat') and s.get('stop_lon')]
        result[n] = {'nucleo':n,'fecha_trazados':version,'trazados':{'type':'FeatureCollection','features':features},'estaciones':stations}
        print(f'{n}: {len(features)} trazados, {len(stations)} estaciones')
    output = data_root / 'mapa/redes.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
    temporary.replace(output)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-root',default=os.environ.get('DATA_ROOT','/data'))
    parser.add_argument('--gtfs-zip',type=Path,help='ZIP local alternativo; conserva los datos originales')
    parser.add_argument('--version',help='Fecha de la versión GTFS (por defecto, última descargada)')
    args = parser.parse_args()
    root = Path(args.data_root)
    versions = sorted((root/'gtfs_static').glob('version=*'))
    if not args.version and not versions:
        parser.error('Descarga primero el GTFS con make gtfs')
    version = args.version or versions[-1].name.split('=',1)[1]
    archive = args.gtfs_zip or root/'gtfs_static'/f'version={version}'/'feed.zip'
    if not archive.is_file():
        parser.error('No existe el ZIP; ejecuta make gtfs o indica --gtfs-zip')
    prepare(root,archive,version)

if __name__ == '__main__':
    main()
