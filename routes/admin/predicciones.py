# routes/admin/predicciones.py
import calendar
import json
import os
import threading
from collections import Counter
from datetime import date, datetime, timedelta

import joblib
import pandas as pd
from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import text

from models import DIAS_SEMANA, Horario, ProgramacionViaje, Ruta, db
from routes.utils.feriados import es_feriado_peru

predicciones_bp = Blueprint('predicciones', __name__, url_prefix='/admin/predicciones')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
ML_DIR = os.path.join(BASE_DIR, 'ml', 'modelos')
MODEL_PATH = os.path.join(ML_DIR, 'modelo_ocupacion.joblib')
METRICAS_PATH = os.path.join(ML_DIR, 'metricas.json')
HIST_PATH = os.path.join(ML_DIR, 'historial.json')

_cache = {'mtime': None, 'modelo': None, 'metricas': None}
_lock = threading.Lock()


# ---------------------------------------------------------------------
# Carga del modelo (se recarga sola si vuelves a entrenar)
# ---------------------------------------------------------------------
def _cargar():
    if not (os.path.exists(MODEL_PATH) and os.path.exists(METRICAS_PATH)):
        return None, None
    mtime = os.path.getmtime(MODEL_PATH)
    if _cache['mtime'] != mtime:
        _cache['modelo'] = joblib.load(MODEL_PATH)
        with open(METRICAS_PATH, encoding='utf-8') as f:
            _cache['metricas'] = json.load(f)
        _cache['mtime'] = mtime
    return _cache['modelo'], _cache['metricas']


def _historial():
    if os.path.exists(HIST_PATH):
        with open(HIST_PATH, encoding='utf-8') as f:
            return json.load(f)
    return []


def _total_viajes_base():
    return db.session.execute(text("SELECT COUNT(*) FROM v_dataset_ocupacion")).scalar() or 0


def _capacidad_ruta(id_ruta):
    caps = [h.vehiculo_default.capacidad_asientos
            for h in Horario.query.filter_by(id_ruta=id_ruta).all() if h.vehiculo_default]
    return Counter(caps).most_common(1)[0][0] if caps else 40


def _fila(ruta, fecha, hora_dec, capacidad, precio=None):
    fer = es_feriado_peru(fecha)
    vis = es_feriado_peru(fecha + timedelta(days=1))
    if precio is None:
        precio = round(float(ruta.precio_base) * (1.10 if (fer or vis) else 1.0) * 2) / 2
    return {
        'dia_semana_num': fecha.weekday(), 'mes': fecha.month, 'dia_mes': fecha.day,
        'es_fin_semana': int(fecha.weekday() in (4, 5, 6)),
        'es_feriado': int(fer), 'es_vispera': int(vis),
        'id_ruta': ruta.id_ruta, 'id_sede_origen': ruta.id_sede_origen,
        'id_sede_destino': ruta.id_sede_destino, 'distancia_km': float(ruta.distancia_km),
        'hora_salida_decimal': float(hora_dec), 'precio_pasaje': float(precio),
        'capacidad_asientos': int(capacidad),
    }


def _probabilidades(modelo, filas):
    df = pd.DataFrame(filas)[modelo['features']]
    return modelo['pipeline'].predict_proba(df)[:, 1]


def _nombre_ruta(r):
    o = r.origen.nombre_sede if r.origen else '?'
    d = r.destino.nombre_sede if r.destino else '?'
    return f"{o} → {d}"


def proyectar_ruta(ruta, d1, d2):
    """Predice, para cada día entre d1 y d2, las salidas del horario recurrente de la ruta.
    Devuelve {'AAAA-MM-DD': {'feriado': bool, 'salidas': [{hora, placa, prob}], 'max': prob}}."""
    modelo, _ = _cargar()
    if not modelo:
        return {}
    por_dia = {}
    for h in Horario.query.filter_by(id_ruta=ruta.id_ruta, estado='Activo').all():
        por_dia.setdefault(DIAS_SEMANA.index(h.dia_semana), []).append(h)
    cap_ruta = _capacidad_ruta(ruta.id_ruta)

    filas, meta = [], []
    d = d1
    while d <= d2:
        fer = es_feriado_peru(d)
        pico = fer or es_feriado_peru(d + timedelta(days=1))
        for h in por_dia.get(d.weekday(), []):
            veh = h.vehiculo_default
            cap = veh.capacidad_asientos if veh else cap_ruta
            precio = round(float(h.precio_pasaje_base) * (1.10 if pico else 1.0) * 2) / 2
            filas.append(_fila(ruta, d, h.hora_salida.hour + h.hora_salida.minute / 60, cap, precio))
            meta.append((d, fer, h.hora_salida.strftime('%H:%M'), veh.placa if veh else '—'))
        d += timedelta(days=1)

    out = {}
    if filas:
        for (dia, fer, hora, placa), p in zip(meta, _probabilidades(modelo, filas)):
            reg = out.setdefault(dia.isoformat(), {'feriado': fer, 'salidas': [], 'max': 0})
            prob = round(float(p) * 100, 1)
            reg['salidas'].append({'hora': hora, 'placa': placa, 'prob': prob})
            reg['max'] = max(reg['max'], prob)
    # los feriados también se marcan en días sin salida
    d = d1
    while d <= d2:
        if es_feriado_peru(d):
            out.setdefault(d.isoformat(), {'feriado': True, 'salidas': [], 'max': None})
        d += timedelta(days=1)
    return out


# ---------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------
@predicciones_bp.route('/')
def dashboard_predicciones():
    modelo, metricas = _cargar()
    if not modelo:
        return render_template('admin/predicciones.html', metricas=None, rutas=[],
                               historial=[], nuevos=0, total_actual=0)

    rutas = [{'id': r.id_ruta, 'nombre': _nombre_ruta(r),
              'precio': float(r.precio_base), 'capacidad': _capacidad_ruta(r.id_ruta)}
             for r in Ruta.query.filter_by(activa=True).order_by(Ruta.id_ruta).all()]

    total_actual = _total_viajes_base()
    nuevos = max(0, total_actual - metricas['filas']['total'])
    return render_template('admin/predicciones.html', metricas=metricas, rutas=rutas,
                           historial=_historial(), nuevos=nuevos, total_actual=total_actual)


# ---------------------------------------------------------------------
# Calendario de calor
# ---------------------------------------------------------------------
@predicciones_bp.route('/calendario')
def calendario():
    if not _cargar()[0]:
        return jsonify(error='Modelo no entrenado.'), 400
    try:
        ruta = db.session.get(Ruta, int(request.args['id_ruta']))
        anio, mes = [int(x) for x in request.args['mes'].split('-')]
        d1 = date(anio, mes, 1)
        d2 = date(anio, mes, calendar.monthrange(anio, mes)[1])
    except (KeyError, ValueError, TypeError):
        return jsonify(error='Parámetros inválidos.'), 400
    if not ruta:
        return jsonify(error='La ruta no existe.'), 404
    return jsonify(dias=proyectar_ruta(ruta, d1, d2), primer_dia=d1.weekday(), total_dias=d2.day)


# ----------------------------------------------------------------
# Reentrenamiento del modelo
# ----------------------------------------------------------------

@predicciones_bp.route('/reentrenar', methods=['POST'])
def reentrenar():
    if not _lock.acquire(blocking=False):
        return jsonify(error='Ya hay un entrenamiento en curso.'), 409
    try:
        from ml.entrenar_modelo import entrenar
        registro = entrenar()
        _cache['mtime'] = None
        return jsonify(registro)
    except Exception as e:
        return jsonify(error=f'Falló el entrenamiento: {e}'), 500
    finally:
        _lock.release()