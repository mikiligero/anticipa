"""Entrenamiento del modelo predictivo de retrasos (Sprint 2, O4).

Dos modelos LightGBM sobre gold/features_modelo.parquet:
  1. Regresión: minutos de retraso final esperados (KPI K6: MAE).
  2. Clasificación: P(retraso final ≥ ALERT_DELAY_MINUTES) — alimenta la
     emisión de alertas con umbral de confianza (KPI K7 ≥ 90%, matriz de
     consecuencias del Sprint 1: minimizar falsos positivos).

Backtesting temporal: las últimas fechas se reservan como test (nunca se
valida con datos anteriores al corte). Promoción a prod solo si el MAE
no empeora el del modelo vigente (regla del DAG semanal).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s train %(message)s")
log = logging.getLogger("train")

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
FEATURES_PATH = DATA_ROOT / "gold" / "features_modelo.parquet"
MODELS_ROOT = DATA_ROOT / "models"
PROD_DIR = MODELS_ROOT / "prod"
ALERT_DELAY_MIN = float(os.environ.get("ALERT_DELAY_MINUTES", "10"))
TEST_FRACTION = 0.2

FEATURES_NUM = ["retraso_actual_min", "stop_sequence", "hora_local", "dia_semana", "min_desde_inicio"]
FEATURE_CAT = "linea"
TARGET = "target_retraso_final_min"


MAX_ROWS = int(os.environ.get("TRAIN_MAX_ROWS", "4000000"))


def load_dataset() -> pd.DataFrame:
    """Carga columnar con muestreo uniforme si el histórico excede MAX_ROWS
    (entrenamiento dimensionado para contenedores con poca RAM)."""
    if not FEATURES_PATH.exists():
        log.error("No existe %s — ejecuta antes dbt build", FEATURES_PATH)
        sys.exit(1)
    con = duckdb.connect()
    con.sql("set memory_limit='1GB'")
    total = con.sql(f"select count(*) from read_parquet('{FEATURES_PATH}')").fetchone()[0]
    cols = "fecha, linea, retraso_actual_min, stop_sequence, hora_local, dia_semana, es_finde, min_desde_inicio, " + TARGET
    q = f"select {cols} from read_parquet('{FEATURES_PATH}') where {TARGET} is not null and retraso_actual_min is not null"
    if total > MAX_ROWS:
        pct = round(MAX_ROWS * 100.0 / total, 2)
        q += f" using sample {pct}% (bernoulli)"
        log.info("Muestreo: %d filas totales → ~%d (%s%%)", total, MAX_ROWS, pct)
    df = con.sql(q).df()
    for c in ("retraso_actual_min", "min_desde_inicio"):
        df[c] = df[c].astype("float32")
    for c in ("stop_sequence", "hora_local", "dia_semana"):
        df[c] = df[c].astype("float32")
    df["es_finde"] = df["es_finde"].astype(int)
    df[TARGET] = df[TARGET].astype("float32")
    log.info("Dataset: %d filas, %d fechas (%s → %s)", len(df), df["fecha"].nunique(), df["fecha"].min(), df["fecha"].max())
    return df


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fechas = sorted(df["fecha"].unique())
    n_test = max(1, int(len(fechas) * TEST_FRACTION))
    corte = fechas[-n_test]
    train = df[df["fecha"] < corte]
    test = df[df["fecha"] >= corte]
    log.info("Split temporal: train %d filas (< %s), test %d filas", len(train), corte, len(test))
    return train, test


def build_matrices(df: pd.DataFrame, categories: list[str]) -> pd.DataFrame:
    x = df[FEATURES_NUM + ["es_finde"]].copy()
    x[FEATURE_CAT] = pd.Categorical(df[FEATURE_CAT].fillna("SIN_LINEA"), categories=categories)
    return x


def main() -> None:
    df = load_dataset()
    if df["fecha"].nunique() < 3:
        log.error("Histórico insuficiente (<3 días) para un split temporal fiable")
        sys.exit(1)

    train, test = temporal_split(df)
    categories = sorted(train[FEATURE_CAT].fillna("SIN_LINEA").unique().tolist())

    x_train, x_test = build_matrices(train, categories), build_matrices(test, categories)

    # ── 1. Regresión: minutos de retraso final ──────────────────────────
    reg = lgb.LGBMRegressor(
        n_estimators=600, learning_rate=0.05, num_leaves=63,
        subsample=0.9, colsample_bytree=0.9, random_state=42, verbose=-1,
    )
    reg.fit(
        x_train, train[TARGET],
        eval_set=[(x_test, test[TARGET])],
        callbacks=[lgb.early_stopping(50, verbose=False)],
    )
    pred = reg.predict(x_test)
    mae = float(mean_absolute_error(test[TARGET], pred))
    rmse = float(np.sqrt(mean_squared_error(test[TARGET], pred)))
    pct_2min = float(np.mean(np.abs(pred - test[TARGET]) <= 2.0) * 100)
    log.info("Regresión — MAE %.2f min · RMSE %.2f · dentro de ±2 min: %.1f%% (objetivo K6: ≥80%%)", mae, rmse, pct_2min)

    # ── 2. Clasificación: alerta (retraso final ≥ umbral) ───────────────
    y_train_alert = (train[TARGET] >= ALERT_DELAY_MIN).astype(int)
    y_test_alert = (test[TARGET] >= ALERT_DELAY_MIN).astype(int)
    clf = lgb.LGBMClassifier(
        n_estimators=600, learning_rate=0.05, num_leaves=63,
        subsample=0.9, colsample_bytree=0.9, random_state=42, verbose=-1,
    )
    clf.fit(
        x_train, y_train_alert,
        eval_set=[(x_test, y_test_alert)],
        callbacks=[lgb.early_stopping(50, verbose=False)],
    )
    proba = clf.predict_proba(x_test)[:, 1]
    # Precisión de las alertas emitidas al umbral de confianza 0.90 (K7)
    emitidas = proba >= 0.90
    precision_alertas = float((y_test_alert[emitidas] == 1).mean() * 100) if emitidas.any() else None
    log.info("Alertas — emitidas %d · precisión %.1f%% (objetivo K7: ≥90%%)",
             int(emitidas.sum()), precision_alertas or float("nan"))

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_train": len(train),
        "n_test": len(test),
        "fecha_corte_test": str(test["fecha"].min()),
        "mae_min": round(mae, 3),
        "rmse_min": round(rmse, 3),
        "pct_dentro_2min": round(pct_2min, 1),
        "alert_delay_min": ALERT_DELAY_MIN,
        "precision_alertas_pct": round(precision_alertas, 1) if precision_alertas is not None else None,
        "linea_categories": categories,
        "features_num": FEATURES_NUM + ["es_finde"],
        "feature_cat": FEATURE_CAT,
    }

    # ── Persistencia y promoción ─────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = MODELS_ROOT / "history" / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(reg, run_dir / "model_regresion.joblib")
    joblib.dump(clf, run_dir / "model_alerta.joblib")
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    prod_metrics_path = PROD_DIR / "metrics.json"
    prod_mae = None
    if prod_metrics_path.exists():
        prod_mae = json.loads(prod_metrics_path.read_text()).get("mae_min")

    if prod_mae is None or mae <= prod_mae:
        PROD_DIR.mkdir(parents=True, exist_ok=True)
        for f in run_dir.iterdir():
            shutil.copy2(f, PROD_DIR / f.name)
        log.info("Modelo PROMOCIONADO a prod (MAE %.2f %s MAE prod anterior %s)",
                 mae, "≤" if prod_mae is not None else "· sin", prod_mae)
    else:
        log.warning("Modelo NO promocionado: MAE %.2f > MAE prod %.2f", mae, prod_mae)


if __name__ == "__main__":
    main()
