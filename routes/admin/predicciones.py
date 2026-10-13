# routes/admin/predicciones.py
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta
import threading
from sqlalchemy import text
from models import db

import joblib
import pandas as pd
from flask import Blueprint, jsonify, render_template, request

from models import Horario, ProgramacionViaje, Ruta
from routes.utils.feriados import es_feriado_peru

predicciones_bp = Blueprint('predicciones', __name__, url_prefix='/admin/predicciones')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
ML_DIR = os.path.join(BASE_DIR, 'ml', 'modelos')
MODEL_PATH = os.path.join(ML_DIR, 'modelo_ocupacion.joblib')
METRICAS_PATH = os.path.join(ML_DIR, 'metricas.json')

CLIMAS = ['despejado', 'neblina', 'lluvia', 'granizo']
_cache = {'mtime': None, 'modelo': None, 'metricas': None}

HIST_PATH = os.path.join(ML_DIR, 'historial.json')
_lock = threading.Lock()


def _historial():
    if os.path.exists(HIST_PATH):
        with open(HIST_PATH, encoding='utf-8') as f:
            return json.load(f)
    return []


def _total_viajes_base():
    return db.session.execute(text("SELECT COUNT(*) FROM v_dataset_ocupacion")).scalar() or 0


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


def _capacidad_ruta(id_ruta):
    """Capacidad más común de los buses asignados a los horarios de la ruta."""
    caps = [h.vehiculo_default.capacidad_asientos
            for h in Horario.query.filter_by(id_ruta=id_ruta).all()
            if h.vehiculo_default]
    return Counter(caps).most_common(1)[0][0] if caps else 40


def _fila(ruta, fecha, hora_dec, clima, capacidad, precio=None):
    """Arma las variables que el modelo espera (mismas que en el entrenamiento)."""
    fer = es_feriado_peru(fecha)
    vis = es_feriado_peru(fecha + timedelta(days=1))
    if precio is None:
        precio = round(float(ruta.precio_base) * (1.10 if (fer or vis) else 1.0) * 2) / 2
    return {
        'dia_semana_num': fecha.weekday(),
        'mes': fecha.month,
        'dia_mes': fecha.day,
        'es_fin_semana': int(fecha.weekday() in (4, 5, 6)),
        'es_feriado': int(fer),
        'es_vispera': int(vis),
        'id_ruta': ruta.id_ruta,
        'id_sede_origen': ruta.id_sede_origen,
        'id_sede_destino': ruta.id_sede_destino,
        'distancia_km': float(ruta.distancia_km),
        'hora_salida_decimal': float(hora_dec),
        'precio_pasaje': float(precio),
        'capacidad_asientos': int(capacidad),
        'clima': clima if clima in CLIMAS else 'despejado',
    }


def _probabilidades(modelo, filas):
    df = pd.DataFrame(filas)[modelo['features']]
    return modelo['pipeline'].predict_proba(df)[:, 1]


def _nombre_ruta(r):
    o = r.origen.nombre_sede if r.origen else '?'
    d = r.destino.nombre_sede if r.destino else '?'
    return f"{o} → {d}"


# ---------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------
@predicciones_bp.route('/')
def dashboard_predicciones():
    modelo, metricas = _cargar()
    if not modelo:
        return render_template('admin/predicciones.html', metricas=None, rutas=[], proximos=[],
                               climas=CLIMAS, historial=[], nuevos=0, total_actual=0)

    rutas = [{'id': r.id_ruta, 'nombre': _nombre_ruta(r),
              'precio': float(r.precio_base), 'capacidad': _capacidad_ruta(r.id_ruta)}
             for r in Ruta.query.filter_by(activa=True).order_by(Ruta.id_ruta).all()]

    hoy = date.today()
    viajes = (ProgramacionViaje.query
              .filter(ProgramacionViaje.estado_viaje == 'Programado',
                      ProgramacionViaje.fecha_salida >= hoy,
                      ProgramacionViaje.fecha_salida <= hoy + timedelta(days=14))
              .order_by(ProgramacionViaje.salida_programada).limit(25).all())

    filas, info = [], []
    for v in viajes:
        h = v.horario
        veh = v.vehiculo_efectivo
        if not (h and h.ruta and veh):
            continue
        hs = v.salida_programada
        filas.append(_fila(h.ruta, v.fecha_salida, hs.hour + hs.minute / 60,
                           v.clima or 'despejado', veh.capacidad_asientos, float(v.precio_pasaje)))
        info.append({'fecha': v.fecha_salida, 'hora': hs.strftime('%H:%M'),
                     'ruta': _nombre_ruta(h.ruta), 'placa': veh.placa,
                     'capacidad': veh.capacidad_asientos})

    proximos = []
    if filas:
        for d, p in zip(info, _probabilidades(modelo, filas)):
            d['prob'] = round(float(p) * 100, 1)
            proximos.append(d)

    total_actual = _total_viajes_base()
    nuevos = max(0, total_actual - metricas['filas']['total'])

    return render_template('admin/predicciones.html', metricas=metricas, rutas=rutas,
                           proximos=proximos, climas=CLIMAS, historial=_historial(),
                           nuevos=nuevos, total_actual=total_actual)


# ---------------------------------------------------------------------
# Predicción puntual (la llama el formulario con fetch)
# ---------------------------------------------------------------------
@predicciones_bp.route('/predecir', methods=['POST'])
def predecir():
    modelo, _ = _cargar()
    if not modelo:
        return jsonify(error='Modelo no entrenado. Ejecuta ml/entrenar_modelo.py'), 400

    datos = request.get_json(silent=True) or {}
    try:
        ruta = Ruta.query.get(int(datos['id_ruta']))
        fecha = datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
        hh, mm = [int(x) for x in datos['hora'].split(':')[:2]]
        umbral = float(datos.get('umbral', 0.5))
    except (KeyError, ValueError, TypeError):
        return jsonify(error='Datos incompletos o con formato inválido.'), 400
    if not ruta:
        return jsonify(error='La ruta no existe.'), 404

    clima = datos.get('clima', 'despejado')
    capacidad = _capacidad_ruta(ruta.id_ruta)
    fila = _fila(ruta, fecha, hh + mm / 60, clima, capacidad)
    prob = float(_probabilidades(modelo, [fila])[0])

    if prob >= 0.70:
        recomendacion = 'Demanda muy alta: considera un bus extra o ajustar el precio.'
    elif prob >= umbral:
        recomendacion = 'Se espera un viaje bastante lleno: vigila la venta de pasajes.'
    elif prob >= 0.30:
        recomendacion = 'Ocupación intermedia: operación normal.'
    else:
        recomendacion = 'Demanda baja: una promoción podría ayudar a llenar asientos.'

    return jsonify(
        probabilidad=round(prob * 100, 1),
        alta=bool(prob >= umbral),
        umbral=umbral,
        capacidad=capacidad,
        precio=fila['precio_pasaje'],
        es_feriado=bool(fila['es_feriado']),
        es_vispera=bool(fila['es_vispera']),
        recomendacion=recomendacion,
    )

@predicciones_bp.route('/reentrenar', methods=['POST'])
def reentrenar():
    if not _lock.acquire(blocking=False):
        return jsonify(error='Ya hay un entrenamiento en curso.'), 409
    try:
        from ml.entrenar_modelo import entrenar
        registro = entrenar()
        _cache['mtime'] = None          # fuerza a recargar el modelo
        return jsonify(registro)
    except Exception as e:
        return jsonify(error=f'Falló el entrenamiento: {e}'), 500
    finally:
        _lock.release()