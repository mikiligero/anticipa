"""Inicialización idempotente y reconstrucción del mapa sin archivos intermedios."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import duckdb
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from init_project import initialize
from prepare_map import prepare

class SetupTests(unittest.TestCase):
    def test_credentials_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'.env.example').write_text('API_TOKEN=\nOPERATOR_USER=operador\n')
            with patch('builtins.print'):
                initialize(root)
                before={p.name:p.read_bytes() for p in [root/'.env',root/'.secrets/access.txt',root/'.secrets/operator.htpasswd']}
                initialize(root)
            self.assertEqual(before,{p.name:p.read_bytes() for p in [root/'.env',root/'.secrets/access.txt',root/'.secrets/operator.htpasswd']})
            self.assertNotIn('API_TOKEN=\n',(root/'.env').read_text())

    def test_map_from_raw_zip_with_padded_headers_and_same_line_in_two_nuclei(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'nucleos').mkdir()
            with duckdb.connect() as con:
                con.execute(f"copy (select * from (values ('Málaga','01001'),('Madrid','02001')) t(nucleo,stop_id)) to '{root}/nucleos/estaciones_nucleo.parquet' (format parquet)")
            archive=root/'feed.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('trips.txt','trip_id,route_id,shape_id    \na,ma,shape_ma    \nb,md,shape_md    \n')
                z.writestr('routes.txt','route_id,route_short_name,route_color\nma,C1,0000ff\nmd,C1,ff0000\n')
                z.writestr('stops.txt','stop_id,stop_name,stop_lat,stop_lon\n01001,Málaga,36.7,-4.4\n02001,Madrid,40.4,-3.7\n')
                z.writestr('stop_times.txt','trip_id,stop_id\na,01001\nb,02001\n')
                z.writestr('shapes.txt','shape_id,shape_pt_sequence,shape_pt_lat,shape_pt_lon\nshape_ma,1,36.7,-4.4\nshape_ma,2,36.8,-4.5\nshape_md,1,40.4,-3.7\nshape_md,2,40.5,-3.8\n')
            with patch('builtins.print'):data=prepare(root,archive,'2026-10-30')
            self.assertEqual(data['Málaga']['trazados']['features'][0]['properties']['shape_id'],'shape_ma')
            self.assertEqual(len(data['Málaga']['estaciones']),1)
            self.assertEqual(data['Madrid']['trazados']['features'][0]['properties']['shape_id'],'shape_md')
            self.assertTrue((root/'mapa/redes.json').is_file())

if __name__=='__main__':unittest.main()
