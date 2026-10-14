# ml/entrenar_modelo.py
"""
Entrena el modelo que predice si un viaje tendrá ALTA OCUPACIÓN (>= 70% de asientos).

Lee la vista v_dataset_ocupacion, entrena, guarda:
  - ml/modelos/modelo_ocupacion.joblib   (modelo + lista de variables + umbral)
  - ml/modelos/metricas.json             (todo lo que necesita la interfaz web)

Uso:  python ml/entrenar_modelo.py
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# ---------------------------------------------------------------------
# Configuración (ajusta la conexión a la de tu .env)
# ---------------------------------------------------------------------
DB_URL = ("mysql+pymysql://app_transportes:CambiaEstaClave_456@localhost/"
          "agencia_transportes?charset=utf8mb4")
UMBRAL_ALTA = 0.70
SEMILLA = 42

BASE_DIR = Path(__file__).resolve().parent
SALIDA = BASE_DIR / "modelos"
SALIDA.mkdir(exist_ok=True)

# Variables que el modelo puede conocer ANTES de la salida del viaje.
# (pasajes_vendidos y ocupacion NO entran: son la respuesta, usarlas sería trampa.)
NUMERICAS = ["dia_semana_num", "mes", "dia_mes", "es_fin_semana", "es_feriado", "es_vispera",
             "id_ruta", "id_sede_origen", "id_sede_destino", "distancia_km",
             "hora_salida_decimal", "precio_pasaje", "capacidad_asientos"]
CATEGORICAS = ["clima"]
FEATURES = NUMERICAS + CATEGORICAS

FERIADOS_FIJOS = [(1, 1), (5, 1), (6, 29), (7, 28), (7, 29), (8, 30), (10, 8),
                  (11, 1), (12, 8), (12, 25)]


# ---------------------------------------------------------------------
# Feriados (misma lógica del simulador; la interfaz de predicción la reutilizará)
# ---------------------------------------------------------------------
def pascua(anio):
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def feriados_de(anios):
    out = set()
    for anio in anios:
        for mes, dia in FERIADOS_FIJOS:
            out.add(date(anio, mes, dia))
        p = pascua(anio)
        out.add(p - timedelta(days=3))
        out.add(p - timedelta(days=2))
    return out


# ---------------------------------------------------------------------
# 1. Dataset desde la base de datos
# ---------------------------------------------------------------------
def cargar_dataset():
    engine = create_engine(DB_URL)
    df = pd.read_sql("SELECT * FROM v_dataset_ocupacion", engine)

    # MySQL devuelve Decimal en varias columnas: pasar todo a número
    for col in ["distancia_km", "hora_salida_decimal", "precio_pasaje",
                "capacidad_asientos", "pasajes_vendidos", "ocupacion"]:
        df[col] = df[col].astype(float)
    for col in ["es_fin_semana", "es_feriado"]:
        df[col] = df[col].astype(int)

    df["fecha_salida"] = pd.to_datetime(df["fecha_salida"])
    df["clima"] = df["clima"].fillna("despejado")

    fer = feriados_de(range(df["fecha_salida"].dt.year.min(), df["fecha_salida"].dt.year.max() + 2))
    df["es_vispera"] = df["fecha_salida"].dt.date.map(
        lambda d: int((d + timedelta(days=1)) in fer))

    df["alta_ocupacion"] = (df["ocupacion"] >= UMBRAL_ALTA).astype(int)
    return df.sort_values("fecha_salida").reset_index(drop=True)


# ---------------------------------------------------------------------
# 2. Modelos candidatos
# ---------------------------------------------------------------------
def armar_pipeline(modelo):
    pre = ColumnTransformer(
        [("clima", OneHotEncoder(handle_unknown="ignore"), CATEGORICAS)],
        remainder="passthrough")
    return Pipeline([("pre", pre), ("modelo", modelo)])


CANDIDATOS = {
    "RandomForest": lambda: RandomForestClassifier(
        n_estimators=300, min_samples_leaf=3, random_state=SEMILLA, n_jobs=-1),
    "GradientBoosting": lambda: GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=3, random_state=SEMILLA),
}


def metricas_de(y, pred, proba):
    return {
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "recall": round(recall_score(y, pred, zero_division=0), 4),
        "f1": round(f1_score(y, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y, proba), 4),
        "brier": round(brier_score_loss(y, proba), 4),
    }


# ---------------------------------------------------------------------
# 3. Entrenamiento y evaluación
# ---------------------------------------------------------------------
TOLERANCIA_AUC = 0.01
RUTA_MODELO = SALIDA / "modelo_ocupacion.joblib"
RUTA_METRICAS = SALIDA / "metricas.json"
RUTA_HISTORIAL = SALIDA / "historial.json"


def _leer_historial():
    if RUTA_HISTORIAL.exists():
        with open(RUTA_HISTORIAL, encoding="utf-8") as f:
            return json.load(f)
    return []


def entrenar(forzar=False):
    """Entrena, compara con el modelo actual y lo reemplaza solo si no empeora.
    Devuelve un dict con el resumen del intento (también se guarda en el historial)."""
    df = cargar_dataset()
    n = len(df)
    print(f"Dataset: {n:,} viajes ({df['fecha_salida'].min().date()} a {df['fecha_salida'].max().date()})")
    print(f"Alta ocupación (>= {UMBRAL_ALTA:.0%}): {df['alta_ocupacion'].mean():.1%}")

    # Corte TEMPORAL: lo más antiguo entrena, lo más reciente evalúa
    i_val, i_test = int(n * 0.70), int(n * 0.85)
    train, val, test = df.iloc[:i_val], df.iloc[i_val:i_test], df.iloc[i_test:]
    print(f"Entrenamiento: {len(train):,} | Validación: {len(val):,} | Prueba: {len(test):,}")

    # --- Elegir modelo con la validación ---
    comparacion = {}
    for nombre, fabrica in CANDIDATOS.items():
        pipe = armar_pipeline(fabrica()).fit(train[FEATURES], train["alta_ocupacion"])
        proba = pipe.predict_proba(val[FEATURES])[:, 1]
        comparacion[nombre] = metricas_de(val["alta_ocupacion"], (proba >= 0.5).astype(int), proba)
        print(f"  {nombre:<17} AUC val = {comparacion[nombre]['roc_auc']}  "
              f"F1 val = {comparacion[nombre]['f1']}")
    mejor = max(comparacion, key=lambda k: comparacion[k]["roc_auc"])
    print(f"Modelo elegido: {mejor}")

    # --- Reentrenar con entrenamiento + validación y evaluar en prueba ---
    entrenamiento = pd.concat([train, val])
    modelo = armar_pipeline(CANDIDATOS[mejor]()).fit(
        entrenamiento[FEATURES], entrenamiento["alta_ocupacion"])

    y = test["alta_ocupacion"].to_numpy()
    proba = modelo.predict_proba(test[FEATURES])[:, 1]
    pred = (proba >= 0.5).astype(int)
    m = metricas_de(y, pred, proba)

    clase_comun = int(entrenamiento["alta_ocupacion"].mean() >= 0.5)
    base_accuracy = round(accuracy_score(y, np.full(len(y), clase_comun)), 4)
    cm = confusion_matrix(y, pred, labels=[0, 1])
    frac_real, frac_pred = calibration_curve(y, proba, n_bins=8, strategy="quantile")

    imp = permutation_importance(modelo, test[FEATURES], y, scoring="roc_auc",
                                 n_repeats=10, random_state=SEMILLA)
    importancias = sorted(
        [{"variable": f, "importancia": round(float(v), 4)} for f, v in zip(FEATURES, imp.importances_mean)],
        key=lambda d: d["importancia"], reverse=True)
    dispersion = [{"ocupacion_real": round(float(o), 4), "probabilidad": round(float(p), 4),
                   "alta_real": int(a)}
                  for o, p, a in zip(test["ocupacion"], proba, y)]

    # --- Comparar con el modelo vigente sobre ESTA misma prueba ---
    auc_anterior = None
    if RUTA_MODELO.exists():
        try:
            previo = joblib.load(RUTA_MODELO)
            p_prev = previo["pipeline"].predict_proba(test[previo["features"]])[:, 1]
            auc_anterior = round(roc_auc_score(y, p_prev), 4)
        except Exception as e:
            print(f"No se pudo evaluar el modelo anterior: {e}")
    aceptado = bool(forzar or auc_anterior is None or m["roc_auc"] >= auc_anterior - TOLERANCIA_AUC)

    ahora = datetime.now().isoformat(timespec="seconds")
    print(f"\nAUC nuevo = {m['roc_auc']} | AUC anterior (misma prueba) = {auc_anterior} "
          f"-> {'ACEPTADO' if aceptado else 'RECHAZADO (se conserva el anterior)'}")

    if aceptado:
        joblib.dump({"pipeline": modelo, "features": FEATURES, "umbral_alta": UMBRAL_ALTA,
                     "modelo": mejor, "entrenado_en": ahora}, RUTA_MODELO)
        resumen = {
            "entrenado_en": ahora, "modelo": mejor, "umbral_alta": UMBRAL_ALTA,
            "filas": {"total": n, "entrenamiento": len(train), "validacion": len(val), "prueba": len(test)},
            "periodo": {"desde": str(df["fecha_salida"].min().date()),
                        "hasta": str(df["fecha_salida"].max().date()),
                        "prueba_desde": str(test["fecha_salida"].min().date())},
            "porcentaje_alta_ocupacion": round(float(df["alta_ocupacion"].mean()), 4),
            "comparacion_validacion": comparacion,
            "metricas_prueba": m,
            "accuracy_linea_base": base_accuracy,
            "matriz_confusion": {"vn": int(cm[0, 0]), "fp": int(cm[0, 1]),
                                 "fn": int(cm[1, 0]), "vp": int(cm[1, 1])},
            "calibracion": {"prob_predicha": [round(float(x), 4) for x in frac_pred],
                            "frecuencia_real": [round(float(x), 4) for x in frac_real]},
            "importancia_variables": importancias,
            "dispersion": dispersion,
            "variables": FEATURES,
        }
        with open(RUTA_METRICAS, "w", encoding="utf-8") as f:
            json.dump(resumen, f, ensure_ascii=False, indent=2)

    registro = {"fecha": ahora, "modelo": mejor, "filas": n, "prueba": len(test),
                "auc": m["roc_auc"], "auc_anterior": auc_anterior,
                "accuracy": m["accuracy"], "recall": m["recall"], "f1": m["f1"],
                "aceptado": aceptado}
    historial = _leer_historial()
    historial.append(registro)
    with open(RUTA_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)
    return registro


if __name__ == "__main__":
    entrenar()