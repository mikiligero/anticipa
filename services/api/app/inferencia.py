"""Preparación de variables e inferencia compartida por viajero y operador."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

TZ = ZoneInfo('Europe/Madrid')

def matrices(df: pd.DataFrame, categories, now=None) -> pd.DataFrame:
    now = now or datetime.now(TZ)
    x = pd.DataFrame({
        'retraso_actual_min': df['arrival_delay_min'],
        'stop_sequence': df.get('stop_sequence'),
        'hora_local': now.hour,
        'dia_semana': (now.weekday() + 1) % 7,
        'min_desde_inicio': df.get('min_desde_inicio', pd.Series(None, index=df.index, dtype='float64')),
        'es_finde': int(now.weekday() >= 5),
    }, index=df.index)
    x['linea'] = pd.Categorical(df.get('linea', pd.Series('SIN_LINEA',index=df.index)).fillna('SIN_LINEA'), categories=categories)
    return x

def predecir(df: pd.DataFrame, models):
    if df.empty or not models.load():
        return None
    x = matrices(df, models.meta['linea_categories'])
    out = df.copy()
    out['retraso_final_min'] = models.reg.predict(x).round(1)
    out['prob_grave'] = models.clf.predict_proba(x)[:,1].round(3)
    return out
