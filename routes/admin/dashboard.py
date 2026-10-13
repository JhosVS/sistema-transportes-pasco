# routes/admin/dashboard.py
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import text

from models import ProgramacionViaje, db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Una fila por viaje, con sus pasajes, ingresos y retraso ya calculados
BASE_VIAJES = """
SELECT pv.id_viaje, pv.fecha_salida, pv.estado_viaje, pv.clima, h.id_ruta,
       ve.id_vehiculo, ve.capacidad_asientos AS cap, r.distancia_km AS dist,
       TIMESTAMPDIFF(MINUTE, pv.llegada_programada, pv.llegada_real) AS retraso,
       (SELECT COUNT(*) FROM detalle_pasajes d
         WHERE d.id_viaje = pv.id_viaje AND d.estado <> 'anulado') AS pas,
       (SELECT COALESCE(SUM(d.precio_pagado), 0) FROM detalle_pasajes d
         WHERE d.id_viaje = pv.id_viaje AND d.estado <> 'anulado') AS ing_pas,
       (SELECT COALESCE(SUM(e.precio_pagado), 0) FROM detalle_encomiendas e
         WHERE e.id_viaje = pv.id_viaje) AS ing_enc
FROM programacion_viaje pv
JOIN horarios h ON h.id_horario = pv.id_horario
JOIN rutas r    ON r.id_ruta = h.id_ruta
LEFT JOIN vehiculo ve ON ve.id_vehiculo = COALESCE(pv.id_vehiculo, h.id_vehiculo_default)
WHERE pv.fecha_salida BETWEEN :desde AND :hasta
"""
VIAJES = f"({BASE_VIAJES}) t"
REALIZADO = "t.estado_viaje IN ('Finalizado','En Ruta')"
GRUPOS_EDAD = ['Menos de 18', '18-25', '26-35', '36-50', '51 o más', 'Sin dato']


def _rango():
    try:
        desde = datetime.strptime(request.args['desde'], '%Y-%m-%d').date()
        hasta = datetime.strptime(request.args['hasta'], '%Y-%m-%d').date()
    except (KeyError, ValueError):
        hasta = date.today()
        desde = hasta - timedelta(days=29)
    if desde > hasta:
        desde, hasta = hasta, desde
    return {'desde': desde, 'hasta': hasta}


def _q(sql, params):
    return [dict(r._mapping) for r in db.session.execute(text(sql), params)]


def _f(x, dec=2):
    return round(float(x or 0), dec)


# ---------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------
@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('admin/dashboard.html')


# ---------------------------------------------------------------------
# Todos los reportes del rango (una sola llamada)
# ---------------------------------------------------------------------
@admin_bp.route('/dashboard/api/todo')
def api_todo():
    p = _rango()

    # --- KPIs ---
    k = _q(f"""SELECT COUNT(*) viajes, COALESCE(SUM(pas),0) pas, COALESCE(SUM(cap),0) cap,
                      COALESCE(SUM(ing_pas),0) ing_pas, COALESCE(SUM(ing_enc),0) ing_enc,
                      SUM(CASE WHEN estado_viaje='Finalizado' AND retraso IS NOT NULL THEN 1 ELSE 0 END) fin,
                      SUM(CASE WHEN estado_viaje='Finalizado' AND retraso <= 15 THEN 1 ELSE 0 END) puntuales,
                      AVG(retraso) retraso_prom
               FROM {VIAJES} WHERE {REALIZADO}""", p)[0]
    canc = _q(f"SELECT COUNT(*) n FROM {VIAJES} WHERE t.estado_viaje='Cancelado'", p)[0]['n']
    mant = _q("""SELECT COALESCE(SUM(costo),0) costo FROM mantenimientos
                 WHERE fecha BETWEEN :desde AND :hasta""", p)[0]['costo']

    ingresos = _f(k['ing_pas']) + _f(k['ing_enc'])
    kpis = {
        'viajes': int(k['viajes']),
        'pasajeros': int(k['pas']),
        'ocupacion': round(100 * float(k['pas']) / float(k['cap']), 1) if k['cap'] else None,
        'ing_pasajes': _f(k['ing_pas']),
        'ing_encomiendas': _f(k['ing_enc']),
        'ingresos': ingresos,
        'costo_mant': _f(mant),
        'margen': round(ingresos - _f(mant), 2),
        'puntualidad': round(100 * float(k['puntuales']) / float(k['fin']), 1) if k['fin'] else None,
        'retraso_prom': round(float(k['retraso_prom']), 1) if k['retraso_prom'] is not None else None,
        'cancelados': int(canc),
    }

    # --- Ocupación por día de la semana ---
    semana = [{'dia': int(r['d']), 'ocupacion': round(100 * float(r['pas']) / float(r['cap']), 1)}
              for r in _q(f"""SELECT WEEKDAY(fecha_salida) d, SUM(pas) pas, SUM(cap) cap
                              FROM {VIAJES} WHERE {REALIZADO} GROUP BY d HAVING SUM(cap) > 0
                              ORDER BY d""", p)]

    # --- Pasajeros por ruta ---
    rutas = [{'ruta': f"{r['o']} → {r['d']}", 'pasajeros': int(r['pas'])}
             for r in _q(f"""SELECT so.nombre_sede o, sd.nombre_sede d, SUM(t.pas) pas
                             FROM {VIAJES}
                             JOIN rutas ru ON ru.id_ruta = t.id_ruta
                             JOIN sedes so ON so.id_sede = ru.id_sede_origen
                             JOIN sedes sd ON sd.id_sede = ru.id_sede_destino
                             WHERE {REALIZADO}
                             GROUP BY ru.id_ruta, so.nombre_sede, sd.nombre_sede
                             ORDER BY pas DESC LIMIT 10""", p)]

    # --- Retraso según clima ---
    clima = [{'clima': r['clima'], 'retraso': round(float(r['ret']), 1), 'viajes': int(r['n'])}
             for r in _q(f"""SELECT COALESCE(clima,'sin dato') clima, AVG(retraso) ret, COUNT(*) n
                             FROM {VIAJES}
                             WHERE t.estado_viaje='Finalizado' AND retraso IS NOT NULL
                             GROUP BY COALESCE(clima,'sin dato') ORDER BY ret""", p)]

    # --- Pasajeros por grupo de edad ---
    edades = {r['grupo']: int(r['n']) for r in _q("""
        SELECT CASE WHEN d.fecha_nacimiento IS NULL THEN 'Sin dato'
                    WHEN TIMESTAMPDIFF(YEAR, d.fecha_nacimiento, pv.fecha_salida) < 18 THEN 'Menos de 18'
                    WHEN TIMESTAMPDIFF(YEAR, d.fecha_nacimiento, pv.fecha_salida) <= 25 THEN '18-25'
                    WHEN TIMESTAMPDIFF(YEAR, d.fecha_nacimiento, pv.fecha_salida) <= 35 THEN '26-35'
                    WHEN TIMESTAMPDIFF(YEAR, d.fecha_nacimiento, pv.fecha_salida) <= 50 THEN '36-50'
                    ELSE '51 o más' END grupo, COUNT(*) n
        FROM detalle_pasajes d JOIN programacion_viaje pv ON pv.id_viaje = d.id_viaje
        WHERE d.estado <> 'anulado' AND pv.estado_viaje IN ('Finalizado','En Ruta')
          AND pv.fecha_salida BETWEEN :desde AND :hasta
        GROUP BY grupo""", p)}
    edad = [{'grupo': g, 'pasajeros': edades.get(g, 0)} for g in GRUPOS_EDAD if edades.get(g, 0)]

    # --- Ingresos por método de pago (según fecha de venta) ---
    pagos = [{'metodo': r['metodo_pago'], 'ingresos': _f(r['total'])}
             for r in _q("""SELECT metodo_pago, SUM(monto_total) total FROM reservas_ventas
                            WHERE estado='pagada' AND fecha_emision >= :desde
                              AND fecha_emision < DATE_ADD(:hasta, INTERVAL 1 DAY)
                            GROUP BY metodo_pago ORDER BY total DESC""", p)]

    # --- Flota ---
    uso = {r['id_vehiculo']: r for r in _q(f"""
        SELECT id_vehiculo, COUNT(*) viajes, COALESCE(SUM(dist),0) km
        FROM {VIAJES} WHERE {REALIZADO} AND id_vehiculo IS NOT NULL GROUP BY id_vehiculo""", p)}
    mants = {r['id_vehiculo']: r for r in _q("""
        SELECT id_vehiculo, COUNT(*) n, COALESCE(SUM(dias_inoperativo),0) dias
        FROM mantenimientos WHERE fecha BETWEEN :desde AND :hasta GROUP BY id_vehiculo""", p)}
    vehiculos = _q("SELECT id_vehiculo, placa, tipo, capacidad_asientos, estado FROM vehiculo ORDER BY placa", {})
    flota = [{'placa': v['placa'], 'tipo': v['tipo'], 'asientos': v['capacidad_asientos'],
              'estado': v['estado'],
              'viajes': int(uso.get(v['id_vehiculo'], {}).get('viajes', 0)),
              'km': int(float(uso.get(v['id_vehiculo'], {}).get('km', 0))),
              'mantenimientos': int(mants.get(v['id_vehiculo'], {}).get('n', 0)),
              'dias_fuera': int(mants.get(v['id_vehiculo'], {}).get('dias', 0))}
             for v in vehiculos]
    estado_flota = {}
    for v in vehiculos:
        estado_flota[v['estado']] = estado_flota.get(v['estado'], 0) + 1

    return jsonify(kpis=kpis, semana=semana, rutas=rutas, clima=clima, edad=edad,
                   pagos=pagos, flota=flota, estado_flota=estado_flota,
                   prediccion=_prediccion())


# ---------------------------------------------------------------------
# Serie de pasajeros e ingresos (agrupada)
# ---------------------------------------------------------------------
@admin_bp.route('/dashboard/api/serie')
def api_serie():
    p = _rango()
    agrupar = request.args.get('agrupar', 'dia')
    if agrupar == 'semana':
        clave = "DATE_FORMAT(DATE_SUB(fecha_salida, INTERVAL WEEKDAY(fecha_salida) DAY), '%Y-%m-%d')"
    elif agrupar == 'mes':
        clave = "DATE_FORMAT(fecha_salida, '%Y-%m')"
    else:
        clave = "DATE_FORMAT(fecha_salida, '%Y-%m-%d')"
    filas = _q(f"""SELECT {clave} periodo, SUM(pas) pas, SUM(ing_pas + ing_enc) ing
                   FROM {VIAJES} WHERE {REALIZADO} GROUP BY periodo ORDER BY periodo""", p)
    return jsonify(datos=[{'periodo': r['periodo'], 'pasajeros': int(r['pas']),
                           'ingresos': _f(r['ing'])} for r in filas])


# ---------------------------------------------------------------------
# Conexión con el modelo predictivo
# ---------------------------------------------------------------------
def _prediccion():
    """Probabilidad de alta ocupación de los próximos viajes. Si no hay modelo, devuelve vacío."""
    try:
        from routes.admin.predicciones import _cargar, _fila, _nombre_ruta, _probabilidades
        modelo, _ = _cargar()
        if not modelo:
            return {'disponible': False, 'viajes': []}
        viajes = (ProgramacionViaje.query
                  .filter(ProgramacionViaje.estado_viaje == 'Programado',
                          ProgramacionViaje.fecha_salida >= date.today())
                  .order_by(ProgramacionViaje.salida_programada).limit(8).all())
        filas, info = [], []
        for v in viajes:
            h, veh = v.horario, v.vehiculo_efectivo
            if not (h and h.ruta and veh):
                continue
            hs = v.salida_programada
            filas.append(_fila(h.ruta, v.fecha_salida, hs.hour + hs.minute / 60,
                               v.clima or 'despejado', veh.capacidad_asientos, float(v.precio_pasaje)))
            info.append({'fecha': hs.strftime('%d/%m %H:%M'), 'ruta': _nombre_ruta(h.ruta),
                         'placa': veh.placa})
        if filas:
            for d, pr in zip(info, _probabilidades(modelo, filas)):
                d['prob'] = round(float(pr) * 100, 1)
        return {'disponible': True, 'viajes': info if filas else []}
    except Exception:
        return {'disponible': False, 'viajes': []}