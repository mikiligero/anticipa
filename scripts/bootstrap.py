"""Inicializa catálogos, geometrías y dimensiones; no entrena ni importa históricos."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data-root',default=os.environ.get('DATA_ROOT','/data'))
    parser.add_argument('--dbt-project',default='/opt/dbt')
    args=parser.parse_args()
    root=Path(args.data_root)
    for name in ('warehouse','gold'):
        (root/name).mkdir(parents=True,exist_ok=True)
    scripts=Path(__file__).resolve().parent
    env=dict(os.environ,DATA_ROOT=str(root),DUCKDB_PATH=str(root/'warehouse/cercanias.duckdb'),GOLD_ROOT=str(root/'gold'))
    for script,options in [
        ('download_gtfs_static.py',['--data-root',str(root),'--full']),
        ('download_nucleos.py',[]),
        ('prepare_map.py',['--data-root',str(root)]),
    ]:
        subprocess.run([sys.executable,str(scripts/script),*options],env=env,check=True)
    subprocess.run(['dbt','build','--project-dir',args.dbt_project,'--profiles-dir',args.dbt_project,
                    '--select','+dim_lineas','dim_estaciones','dim_itinerarios'],env=env,check=True)
    print('Catálogos, mapa y dimensiones preparados. Puedes arrancar la plataforma.')
