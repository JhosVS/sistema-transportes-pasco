# asistente/herramientas.py
import functools
from datetime import date, datetime, timedelta

from sqlalchemy import text
from models import Ruta, db

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

import threading
_ctx = threading.local()


def iniciar_registro():
    _ctx.salidas = []


def salidas():
    return getattr(_ctx, "salidas", [])


def segura(fn):
    @functools.wraps(fn)
    def envoltura(*a, **k):
        try:
            res = fn(*a, **k)
        except Exception as e:
            db.session.rollback()
            res = {"error": f"No se pudo obtener el dato: {e}"}
        if hasattr(_ctx, "salidas"):
            _ctx.salidas.append(res)
        return res
    return envoltura

# ------------------------- utilidades -------------------------
def segura(fn):
    """Si una herramienta falla, devuelve un error legible al modelo en vez de romper el chat."""
    @functools.wraps(fn)
    def envoltura(*a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:
            db.session.rollback()
            return {"error": f"No se pudo obtener el dato: {e}"}
    return envoltura


def _q(sql, **p):
    return [dict(r._mapping) for r in db.session.execute(text(sql), p)]


def _desde(dias):
    """Ventana 'últimos N días' igual a la del dashboard (hoy incluido)."""
    return date.today() - timedelta(days=max(1, min(int(dias), 730)) - 1)


def _resumen(d1, d2):
    k = _q("""SELECT COUNT(*) viajes, COALESCE(SUM(pasajes_vendidos),0) pas,
                     COALESCE(SUM(capacidad_asientos),0) cap
              FROM v_dataset_ocupacion WHERE fecha_salida BETWEEN :a AND :b""", a=d1, b=d2)[0]
    ing = _q("""SELECT COALESCE(SUM(dp.precio_pagado),0) t FROM detalle_pasajes dp
                JOIN programacion_viaje pv ON pv.id_viaje = dp.id_viaje
                WHERE dp.estado <> 'anulado' AND pv.fecha_salida BETWEEN :a AND :b
                  AND pv.estado_viaje IN ('Finalizado','En Ruta')""", a=d1, b=d2)[0]["t"]
    canc = _q("""SELECT COUNT(*) n FROM programacion_viaje
                 WHERE estado_viaje='Cancelado' AND fecha_salida BETWEEN :a AND :b""", a=d1, b=d2)[0]["n"]
    return {"desde": str(d1), "hasta": str(d2), "viajes": int(k["viajes"]), "pasajeros": int(k["pas"]),
            "ocupacion_pct": round(100 * float(k["pas"]) / float(k["cap"]), 1) if k["cap"] else None,
            "ingresos_pasajes_soles": round(float(ing), 2), "cancelados": int(canc)}


def _top(dias, limite):
    return _q("""SELECT r.id_ruta, CONCAT(so.ciudad,' -> ',sd.ciudad) ruta, SUM(v.pasajes_vendidos) pas,
                        ROUND(100*SUM(v.pasajes_vendidos)/SUM(v.capacidad_asientos),1) oc
                 FROM v_dataset_ocupacion v JOIN rutas r ON r.id_ruta = v.id_ruta
                 JOIN sedes so ON so.id_sede = r.id_sede_origen
                 JOIN sedes sd ON sd.id_sede = r.id_sede_destino
                 WHERE v.fecha_salida >= :d GROUP BY r.id_ruta, so.ciudad, sd.ciudad
                 ORDER BY pas DESC LIMIT :n""", d=_desde(dias), n=max(1, min(int(limite), 10)))


# ------------------------- AGENTE DE DATOS -------------------------
@segura
def resumen_periodo(dias: int = 30) -> dict:
    """Resumen de los últimos N días: viajes realizados, pasajeros, ocupación %, ingresos por pasajes
    en soles y viajes cancelados."""
    return _resumen(_desde(dias), date.today())


@segura
def resumen_rango(desde: str, hasta: str) -> dict:
    """Resumen entre dos fechas (AAAA-MM-DD, ambas incluidas): viajes, pasajeros, ocupación %,
    ingresos por pasajes en soles y cancelados. Úsala cuando pidan un mes o periodo concreto."""
    try:
        d1 = datetime.strptime(desde, "%Y-%m-%d").date()
        d2 = datetime.strptime(hasta, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"error": "Fechas inválidas; usa el formato AAAA-MM-DD."}
    if d1 > d2:
        d1, d2 = d2, d1
    if (d2 - d1).days > 730:
        return {"error": "El rango máximo es de 2 años."}
    return _resumen(d1, d2)


@segura
def top_rutas(dias: int = 30, limite: int = 5) -> list:
    """Rutas con más pasajeros en los últimos N días, con su ocupación %."""
    return [{"ruta": r["ruta"], "pasajeros": int(r["pas"]), "ocupacion_pct": float(r["oc"])}
            for r in _top(dias, limite)]


@segura
def ocupacion_por_dia_semana(dias: int = 90) -> list:
    """Ocupación promedio % por día de la semana en los últimos N días."""
    return [{"dia": DIAS[int(r["d"])], "ocupacion_pct": float(r["oc"])}
            for r in _q("""SELECT dia_semana_num d,
                                  ROUND(100*SUM(pasajes_vendidos)/SUM(capacidad_asientos),1) oc
                           FROM v_dataset_ocupacion WHERE fecha_salida >= :d
                           GROUP BY dia_semana_num ORDER BY dia_semana_num""", d=_desde(dias))]


@segura
def estado_flota() -> dict:
    """Cantidad de vehículos por estado (Disponible, Mantenimiento, Baja)."""
    return {r["estado"]: int(r["n"]) for r in
            _q("SELECT estado, COUNT(*) n FROM vehiculo GROUP BY estado")}


# ------------------------- AGENTE DE OPERACIONES -------------------------
@segura
def alertas_operacion() -> dict:
    """Alertas: licencias vencidas o por vencer en 60 días, viajes próximos (7 días) sin conductor o
    vehículo, y viajes próximos con un bus en mantenimiento."""
    lic = _q("""SELECT CONCAT(nombres,' ',apellidos) nombre, licencia_vence FROM conductor
                WHERE estado='Activo' AND licencia_vence <= DATE_ADD(CURDATE(), INTERVAL 60 DAY)
                ORDER BY licencia_vence LIMIT 5""")
    base = """FROM programacion_viaje pv JOIN horarios h ON h.id_horario = pv.id_horario
              LEFT JOIN vehiculo ve ON ve.id_vehiculo = COALESCE(pv.id_vehiculo, h.id_vehiculo_default)
              WHERE pv.estado_viaje='Programado'
                AND pv.fecha_salida BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)"""
    sin = _q(f"""SELECT COUNT(*) n {base} AND (ve.id_vehiculo IS NULL OR
                 COALESCE(pv.id_conductor, h.id_conductor_default) IS NULL)""")[0]["n"]
    mant = _q(f"SELECT COUNT(*) n {base} AND ve.estado='Mantenimiento'")[0]["n"]
    return {"licencias": [{"conductor": l["nombre"], "vence": str(l["licencia_vence"])} for l in lic],
            "viajes_sin_conductor_o_vehiculo": int(sin), "viajes_con_bus_en_mantenimiento": int(mant)}


# ------------------------- AGENTE PREDICTOR -------------------------
@segura
def listar_rutas() -> list:
    """Lista las rutas activas con su id (necesario para predecir un viaje de una ruta concreta)."""
    from routes.admin.predicciones import _nombre_ruta
    return [{"id_ruta": r.id_ruta, "ruta": _nombre_ruta(r)}
            for r in Ruta.query.filter_by(activa=True).order_by(Ruta.id_ruta).all()]


@segura
def predecir_viaje(id_ruta: int, fecha: str, hora: str) -> dict:
    """Probabilidad (%) de alta demanda (70% o más de asientos vendidos) para un viaje de UNA ruta.
    fecha en formato AAAA-MM-DD y hora en HH:MM."""
    from routes.admin.predicciones import _capacidad_ruta, _cargar, _fila, _probabilidades
    modelo, _ = _cargar()
    if not modelo:
        return {"error": "El modelo aún no está entrenado."}
    ruta = db.session.get(Ruta, int(id_ruta))
    if not ruta:
        return {"error": "La ruta no existe. Usa listar_rutas."}
    try:
        f = datetime.strptime(fecha, "%Y-%m-%d").date()
        hh, mm = [int(x) for x in hora.split(":")[:2]]
    except (ValueError, AttributeError):
        return {"error": "Fecha u hora con formato inválido."}
    fila = _fila(ruta, f, hh + mm / 60, _capacidad_ruta(ruta.id_ruta))
    prob = float(_probabilidades(modelo, [fila])[0])
    return {"id_ruta": ruta.id_ruta, "probabilidad_alta_ocupacion_pct": round(prob * 100, 1),
            "feriado": bool(fila["es_feriado"]), "vispera_feriado": bool(fila["es_vispera"])}


@segura
def proximos_viajes(limite: int = 5) -> list:
    """Próximos viajes programados con su probabilidad (%) de alta ocupación según el modelo."""
    from routes.admin.dashboard import _prediccion
    return _prediccion()["viajes"][:max(1, min(int(limite), 8))]


@segura
def prediccion_ruta_top(fecha: str, hora: str = "20:00") -> dict:
    """SOLO para '¿cuál es la ruta más concurrida y su probabilidad de llenarse?'. Predice únicamente
    la ruta con más pasajeros de los últimos 30 días. Para cualquier otra ruta (Tarma, Huancayo,
    Huánuco...) NO la uses: usa listar_rutas y predecir_viaje."""
    top = _top(30, 1)
    if not top:
        return {"error": "No hay datos de rutas."}
    p = predecir_viaje(int(top[0]["id_ruta"]), fecha, hora)
    return {"ruta": top[0]["ruta"], "pasajeros_30_dias": int(top[0]["pas"]), **p}

# ------------------------- RECOMENDACIONES -------------------------
@segura
def recomendaciones() -> dict:
    """Devuelve acciones sugeridas para la operación de los próximos 7 días: buses en mantenimiento con
    viajes asignados, viajes sin conductor o vehículo, licencias por vencer y viajes con demanda muy
    alta o muy baja según el modelo predictivo. Úsala cuando pidan recomendaciones o qué hacer."""
    acciones = []

    # 1. Buses en mantenimiento que tienen viajes próximos
    afectados = _q("""SELECT ve.placa, COUNT(*) n, MIN(pv.salida_programada) primero
                      FROM programacion_viaje pv JOIN horarios h ON h.id_horario = pv.id_horario
                      JOIN vehiculo ve ON ve.id_vehiculo = COALESCE(pv.id_vehiculo, h.id_vehiculo_default)
                      WHERE pv.estado_viaje='Programado' AND ve.estado='Mantenimiento'
                        AND pv.fecha_salida BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                      GROUP BY ve.placa""")
    if afectados:
        libres = [f"{v['placa']} ({v['capacidad_asientos']} asientos)" for v in
                  _q("SELECT placa, capacidad_asientos FROM vehiculo WHERE estado='Disponible' LIMIT 5")]
        for a in afectados:
            acciones.append({
                "prioridad": "alta", "tipo": "vehiculo",
                "hallazgo": f"El bus {a['placa']} está en mantenimiento y tiene {a['n']} viaje(s) "
                            f"próximo(s), el primero el {a['primero']:%d/%m %H:%M}.",
                "recomendacion": "Reasignar esos viajes a otro bus. Disponibles: "
                                 + (", ".join(libres) if libres else "ninguno, evaluar cancelar o alquilar.")})

    # 2. Viajes sin conductor o vehículo
    sin = _q("""SELECT COUNT(*) n FROM programacion_viaje pv JOIN horarios h ON h.id_horario = pv.id_horario
                LEFT JOIN vehiculo ve ON ve.id_vehiculo = COALESCE(pv.id_vehiculo, h.id_vehiculo_default)
                WHERE pv.estado_viaje='Programado'
                  AND pv.fecha_salida BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                  AND (ve.id_vehiculo IS NULL
                       OR COALESCE(pv.id_conductor, h.id_conductor_default) IS NULL)""")[0]["n"]
    if sin:
        acciones.append({"prioridad": "alta", "tipo": "personal",
                         "hallazgo": f"{sin} viaje(s) próximo(s) sin conductor o vehículo asignado.",
                         "recomendacion": "Asignar personal y unidad desde Viajes Programados."})

    # 3. Licencias por vencer
    for l in _q("""SELECT CONCAT(nombres,' ',apellidos) nombre, licencia_vence FROM conductor
                   WHERE estado='Activo' AND licencia_vence <= DATE_ADD(CURDATE(), INTERVAL 60 DAY)
                   ORDER BY licencia_vence LIMIT 5"""):
        acciones.append({"prioridad": "media", "tipo": "personal",
                         "hallazgo": f"La licencia de {l['nombre']} vence el {l['licencia_vence']:%d/%m/%Y}.",
                         "recomendacion": "Gestionar la renovación antes de esa fecha."})

    # 4. Demanda prevista (modelo predictivo)
    from routes.admin.dashboard import _prediccion
    for v in _prediccion()["viajes"]:
        p = v.get("prob")
        if p is None:
            continue
        if p >= 70:
            acciones.append({"prioridad": "media", "tipo": "demanda",
                             "hallazgo": f"{v['ruta']} el {v['fecha']}: {p}% de probabilidad de alta ocupación.",
                             "recomendacion": "Considerar un bus extra o revisar el precio."})
        elif p <= 15:
            acciones.append({"prioridad": "baja", "tipo": "demanda",
                             "hallazgo": f"{v['ruta']} el {v['fecha']}: solo {p}% de probabilidad de alta ocupación.",
                             "recomendacion": "Considerar una promoción para llenar asientos."})

    orden = {"alta": 0, "media": 1, "baja": 2}
    acciones.sort(key=lambda a: orden[a["prioridad"]])
    if not acciones:
        return {"mensaje": "Sin hallazgos: la operación de los próximos 7 días está en orden."}
    return {"total": len(acciones), "acciones": acciones[:6]}

@segura
def estado_modelo() -> dict:
    """Estado del modelo predictivo: algoritmo, fecha de entrenamiento, antigüedad en días, AUC en
    prueba, viajes nuevos desde el entrenamiento y si conviene reentrenar."""
    from routes.admin.predicciones import _cargar
    _, m = _cargar()
    if not m:
        return {"error": "El modelo aún no está entrenado."}
    total = int(_q("SELECT COUNT(*) n FROM v_dataset_ocupacion")[0]["n"])
    nuevos = max(0, total - m["filas"]["total"])
    dias = (datetime.now() - datetime.fromisoformat(m["entrenado_en"])).days
    return {"algoritmo": m["modelo"], "entrenado_el": m["entrenado_en"][:10],
            "dias_desde_entrenamiento": dias, "auc_prueba": m["metricas_prueba"]["roc_auc"],
            "viajes_nuevos": nuevos, "conviene_reentrenar": bool(nuevos >= 50 or dias > 30)}

@segura
def demanda_por_dia_semana(id_ruta: int) -> dict:
    """Probabilidad promedio (%) de alta ocupación por día de la semana para UNA ruta, según el modelo,
    proyectada sobre las próximas 4 semanas. Indica qué días tienen más y menos demanda."""
    from routes.admin.predicciones import _nombre_ruta, proyectar_ruta
    ruta = db.session.get(Ruta, int(id_ruta))
    if not ruta:
        return {"error": "La ruta no existe. Usa listar_rutas."}
    hoy = date.today()
    por_dia = {}
    for iso, x in proyectar_ruta(ruta, hoy, hoy + timedelta(days=27)).items():
        if x["max"] is not None:
            por_dia.setdefault(datetime.strptime(iso, "%Y-%m-%d").weekday(), []).append(x["max"])
    if not por_dia:
        return {"error": "Esta ruta no tiene salidas en su horario."}
    return {"ruta": _nombre_ruta(ruta),
            "dias": [{"dia": DIAS[d], "prob_alta_ocupacion_pct": round(sum(v) / len(v), 1)}
                     for d, v in sorted(por_dia.items())]}

@segura
def precios_ruta(origen: str, destino: str) -> list:
    """Precio del pasaje por horario para una ruta, con el vehículo asignado a cada salida.
    origen y destino son ciudades (ej. 'Tarma', 'Cerro de Pasco'). Ordenado del más barato al más caro.
    El precio lo define el horario, no el vehículo."""
    filas = _q("""SELECT h.dia_semana, h.hora_salida, h.precio_pasaje_base precio,
                         ve.placa, ve.tipo, ve.marca, ve.modelo, ve.capacidad_asientos asientos
                  FROM horarios h
                  JOIN rutas r  ON r.id_ruta = h.id_ruta
                  JOIN sedes so ON so.id_sede = r.id_sede_origen
                  JOIN sedes sd ON sd.id_sede = r.id_sede_destino
                  LEFT JOIN vehiculo ve ON ve.id_vehiculo = h.id_vehiculo_default
                  WHERE h.estado = 'Activo' AND so.ciudad LIKE :o AND sd.ciudad LIKE :d
                  ORDER BY h.precio_pasaje_base, h.id_horario""",
              o=f"%{origen.strip()}%", d=f"%{destino.strip()}%")
    if not filas:
        return [{"error": "No hay horarios activos para esa ruta."}]
    return [{"dia": f["dia_semana"], "hora": str(f["hora_salida"])[:5], "precio_soles": float(f["precio"]),
             "vehiculo": f"{f['placa']} ({f['marca']} {f['modelo']}, {f['tipo']}, {f['asientos']} asientos)"
                         if f["placa"] else "sin vehículo asignado"} for f in filas]