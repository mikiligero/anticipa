"""Contrato de variables: conserva índices y comportamiento entre endpoints."""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from inferencia import matrices, predecir

class InferenceTests(unittest.TestCase):
    def test_index_categories_and_calendar(self):
        df=pd.DataFrame({'arrival_delay_min':[3.,8.],'stop_sequence':[1,2],'linea':['C1','NO_EXISTE']},index=[4,9])
        x=matrices(df,['C1'],datetime(2026,10,31,8,tzinfo=ZoneInfo('Europe/Madrid')))
        self.assertEqual(x.index.tolist(),[4,9])
        self.assertTrue(x.min_desde_inicio.isna().all())
        self.assertEqual(x.dia_semana.tolist(),[6,6])
        self.assertEqual(x.es_finde.tolist(),[1,1])
        self.assertTrue(pd.isna(x.linea.loc[9]))
    def test_shared_scoring_and_absent_model(self):
        df=pd.DataFrame({'arrival_delay_min':[3.],'stop_sequence':[2],'linea':['C1']},index=[7])
        models=SimpleNamespace(load=lambda:True,meta={'linea_categories':['C1']},reg=SimpleNamespace(predict=lambda x:np.array([4.25])),clf=SimpleNamespace(predict_proba=lambda x:np.array([[.1234,.8766]])))
        out=predecir(df,models)
        self.assertEqual(out.index.tolist(),[7])
        self.assertEqual(out.prob_grave.iloc[0],.877)
        self.assertNotIn('prob_grave',df)
        models.load=lambda:False
        self.assertIsNone(predecir(df,models))

if __name__=='__main__':unittest.main()
