import importlib.util
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import duckdb
from fastapi import HTTPException

spec = importlib.util.spec_from_file_location('tendencias_tested', Path(__file__).resolve().parents[1] / 'app/tendencias.py')
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)

class TrendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bucket = 1793355000
        self.now = self.bucket + 200
        (self.root/'nucleos').mkdir()
        with duckdb.connect() as con:
            con.execute(f"copy (select * from (values ('Málaga','01001'),('Madrid','02001')) as t(nucleo,stop_id)) to '{self.root}/nucleos/estaciones_nucleo.parquet' (format parquet)")
        mocks = {'main':types.SimpleNamespace(DATA_ROOT=self.root),'viajero':types.SimpleNamespace(_nucleos=lambda:{'Málaga':{'01001'},'Madrid':{'02001'}})}
        p=patch.dict(sys.modules,mocks);p.start();self.addCleanup(p.stop)
        p=patch.object(t.time,'time',return_value=self.now);p.start();self.addCleanup(p.stop)
        t._CACHE.update(at=0,root=None,rows=[])

    def write(self, ts, rows):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day=datetime.fromtimestamp(ts,ZoneInfo('Europe/Madrid')).strftime('%Y-%m-%d')
        base=self.root/'bronze/trip_updates'/f'date={day}';base.mkdir(parents=True,exist_ok=True)
        with duckdb.connect() as con:
            con.execute('create table samples(trip_id varchar, stop_id varchar, arrival_delay int, snapshot_ts bigint, stop_sequence int)')
            con.executemany('insert into samples values (?,?,?,?,?)', [(*r,ts,1) for r in rows])
            con.execute(f"copy samples to '{base}/part-{ts}.parquet' (format parquet)")

    def test_latest_per_trip_same_line_different_nuclei_and_missing_bins(self):
        self.write(self.bucket+10,[(' a ','01001',0),('b','01001',120),('c','02001',3000)])
        self.write(self.bucket+100,[('a','01001',480),('bad','01001',8000)])
        m=t.tendencias('Málaga'); r=m['serie'][-1]
        self.assertEqual(len(m['serie']),24)
        self.assertEqual(r['trenes'],2)
        self.assertAlmostEqual(r['retraso_medio_min'],5.)
        self.assertAlmostEqual(r['retraso_p90_min'],7.4)
        self.assertAlmostEqual(r['puntualidad_pct'],50.)
        self.assertIsNone(m['serie'][0]['retraso_medio_min'])
        self.assertTrue(r['en_curso'])
        self.assertEqual(t.tendencias('Madrid')['serie'][-1]['retraso_medio_min'],50.)
        with sqlite3.connect(self.root/'tendencias/resumen.sqlite3') as con:
            self.assertEqual(con.execute('select count(*) from muestras').fetchone()[0],2)

    def test_incomplete_capture_does_not_break_available_series(self):
        self.write(self.bucket+10,[('a','01001',60)])
        directory=next((self.root/'bronze/trip_updates').iterdir())
        (directory/f'part-{self.bucket+20}.parquet').write_bytes(b'')
        with self.assertLogs(t.__name__,level='WARNING'):
            result=t.tendencias('Málaga')
        self.assertEqual(result['serie'][-1]['trenes'],1)
        self.assertTrue((directory/f'part-{self.bucket+20}.parquet').exists())

    def test_empty_and_unknown(self):
        self.assertTrue(all(r['retraso_p90_min'] is None for r in t.tendencias('Málaga')['serie']))
        with self.assertRaises(HTTPException):t.tendencias('Desconocido')

if __name__ == '__main__':unittest.main(verbosity=2)
