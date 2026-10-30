"""Verifica aislamiento entre núcleos y exclusión de posiciones no fiables."""
import importlib.util
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from fastapi import HTTPException

spec = importlib.util.spec_from_file_location('mapa_tested', Path(__file__).resolve().parents[1] / 'app/mapa.py')
mapa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapa)

class MapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.core = types.SimpleNamespace(DATA_ROOT=self.root, REALTIME=self.root / 'realtime')
        self.core.REALTIME.mkdir()
        viajero = types.SimpleNamespace(_nucleos=lambda: {'Málaga': {'01001'}, 'Madrid': {'02001'}}, _norm_stop=lambda s: str(s).strip().zfill(5), nivel_de=lambda d: 'normal' if d is None or d < 2 else 'grave')
        self.mock = patch.dict(sys.modules, {'main': self.core, 'viajero': viajero})
        self.mock.start()
        self.addCleanup(self.mock.stop)
        mapa._read_network.cache_clear()

    def test_positions_are_scoped_recent_valid_and_not_cross_joined(self):
        now = int(time.time())
        rows = [
            ('a',' a ','01001',now,36.6,-4.5),
            ('b','b','02001',now,40.4,-3.7),
            ('c','c','01001',now-301,36.6,-4.5),
            ('d','d','01001',now,0.,0.),
            ('e','e','01001',now,99.,-4.5),
            ('f','f','01001',now+120,36.6,-4.5),
            ('g',None,'01001',now,36.6,-4.5),
            ('h','h',None,now,36.7,-4.4),
        ]
        vp = pd.DataFrame(rows, columns=['vehicle_id','trip_id','stop_id','snapshot_ts','latitude','longitude'])
        vp['linea_label'] = 'C1'
        vp.to_parquet(self.core.REALTIME / 'posiciones.parquet')
        pd.DataFrame({'trip_id': ['a','h'], 'stop_id': ['01001','01001'], 'linea': ['C1','C1'], 'stop_name': ['Fuengirola','Málaga'], 'snapshot_ts': [now,now], 'arrival_delay_min': [5.,2.]}).to_parquet(self.core.REALTIME / 'estado_red.parquet')
        result = mapa.trenes('Málaga')
        self.assertEqual({r['id'] for r in result['trenes']}, {'a','h'})
        self.assertEqual(result['trenes'][0]['retraso_min'],5.)
        self.assertEqual({r['id'] for r in mapa.trenes('Madrid')['trenes']}, {'b'})

    def test_unknown_nucleus_never_returns_all_trains(self):
        with self.assertRaises(HTTPException) as e: mapa.trenes('Desconocido')
        self.assertEqual(e.exception.status_code,404)
        self.assertEqual(mapa.trenes('Málaga')['trenes'],[])

    def test_static_network_is_scoped_and_unknown_is_rejected(self):
        p = self.root / 'mapa/redes.json'; p.parent.mkdir()
        p.write_text(json.dumps({'Málaga': {'nucleo':'Málaga','trazados':{'features':[{'id':'32_C1'}]}}, 'Madrid': {'nucleo':'Madrid','trazados':{'features':[{'id':'10_C1'}]}}}))
        self.assertEqual(mapa.red('Málaga')['trazados']['features'], [{'id':'32_C1'}])
        with self.assertRaises(HTTPException): mapa.red('Desconocido')

if __name__ == '__main__': unittest.main(verbosity=2)
