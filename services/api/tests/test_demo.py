"""Contratos de la demo: datos en vivo, aislamiento y autenticación."""
import importlib
import os
import secrets
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))


class DemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.token = secrets.token_urlsafe(32)
        cls.env = patch.dict(os.environ, DATA_ROOT=str(root), API_TOKEN=cls.token)
        cls.env.start()
        cls.core = importlib.import_module('main')
        cls.client = TestClient(cls.core.app)
        realtime = root / 'gold/realtime'
        realtime.mkdir(parents=True)
        (root / 'nucleos').mkdir()
        pd.DataFrame({'nucleo': ['Madrid', 'Málaga'], 'stop_id': ['02001', '01001']}).to_parquet(
            root / 'nucleos/estaciones_nucleo.parquet')
        pd.DataFrame({
            'trip_id': ['viaje-madrid', 'viaje-malaga'],
            'linea': ['C1', 'C1'], 'stop_id': ['02001', '01001'],
            'stop_name': ['Estación Madrid', 'Estación Málaga'],
            'arrival_delay_min': [6.0, 1.0], 'arrival_time': [time.time(), time.time()],
            'stop_sequence': [2, 3], 'semaforo': ['ambar', 'verde'],
            'updated_at': ['2026-10-30T15:00:00Z'] * 2,
        }).to_parquet(realtime / 'estado_red.parquet')

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.env.stop()
        cls.tmp.cleanup()

    def test_operator_data_stays_protected(self):
        self.assertEqual(self.client.get('/salud').status_code, 200)
        self.assertEqual(self.client.get('/estado').status_code, 401)
        self.assertEqual(self.client.get('/estado', headers={'X-API-Key': self.token}).status_code, 200)
        self.assertEqual(self.client.get('/prediccion', headers={'X-API-Key': self.token}).status_code, 404)

    def test_live_line_and_train_do_not_need_a_model(self):
        response = self.client.get('/app/linea/C1', params={'nucleo': 'Madrid'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([t['trip_id'] for t in data['trenes']], ['viaje-madrid'])
        self.assertEqual(data['retraso_medio_min'], 6.0)
        self.assertNotIn('prediccion', data)
        response = self.client.get('/app/tren/viaje-malaga')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['tren']['proxima_parada'], 'Estación Málaga')
        self.assertNotIn('prediccion', response.json())

    def test_unavailable_train_returns_not_found(self):
        self.assertEqual(self.client.get('/app/tren/no-existe').status_code, 404)


if __name__ == '__main__':
    unittest.main()
