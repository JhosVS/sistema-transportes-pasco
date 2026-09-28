# routes/admin/predicciones.py
from flask import Blueprint, render_template
import pandas as pd
import joblib
import os
import json
from database.db import get_connection

predicciones_bp = Blueprint('predicciones', __name__, url_prefix='/admin/predicciones')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
MODEL_PATH = os.path.join(BASE_DIR, 'modelo_demanda.joblib')

modelo = None
if os.path.exists(MODEL_PATH):
    try:
        modelo = joblib.load(MODEL_PATH)
    except Exception as e:
        print(f"Error al cargar modelo: {e}")

@predicciones_bp.route('/')
def dashboard_predicciones():
    if not modelo:
        return "El archivo modelo_demanda.joblib no se encuentra en la raíz del proyecto.", 500

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                pv.id_viaje,
                pv.fecha_salida,
                WEEKDAY(pv.fecha_salida) AS dia_semana_num,
                MONTH(pv.fecha_salida) AS mes,
                DAY(pv.fecha_salida) AS dia_mes,
                CASE WHEN WEEKDAY(pv.fecha_salida) IN (4, 5, 6) THEN 1 ELSE 0 END AS es_fin_semana,
                h.id_ruta,
                so.nombre_sede AS origen,
                sd.nombre_sede AS destino,
                r.id_sede_origen,
                r.id_sede_destino,
                TIME_TO_SEC(h.hora_salida) / 3600 AS hora_salida_decimal,
                h.hora_salida,
                h.precio_pasaje_base,
                v.capacidad_asientos
            FROM programacion_viaje pv
            INNER JOIN horarios h ON pv.id_horario = h.id_horario
            INNER JOIN rutas r ON h.id_ruta = r.id_ruta
            INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
            INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
            INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
            LIMIT 200
        """
        cursor.execute(query)
        viajes = cursor.fetchall()
        cursor.close()
        conn.close()

        # Estructura limpia para el gráfico: { 'Ruta A -> B': [Lun, Mar, Mié, Jue, Vie, Sáb, Dom] }
        rutas_semana = {}
        conteo_rutas_semana = {}

        total_estimado = 0
        total_capacidad = 0

        for v in viajes:
            df_input = pd.DataFrame([{
                'dia_semana_num': int(v['dia_semana_num']),
                'mes': int(v['mes']),
                'dia_mes': int(v['dia_mes']),
                'es_fin_semana': int(v['es_fin_semana']),
                'id_ruta': int(v['id_ruta']),
                'id_sede_origen': int(v['id_sede_origen']),
                'id_sede_destino': int(v['id_sede_destino']),
                'hora_salida_decimal': float(v['hora_salida_decimal']),
                'precio_pasaje_base': float(v['precio_pasaje_base']),
                'capacidad_asientos': int(v['capacidad_asientos'])
            }])

            prediccion_raw = modelo.predict(df_input)[0]
            pasajes_est = max(0, min(v['capacidad_asientos'], int(round(prediccion_raw))))
            pct_ocupacion = round((pasajes_est / v['capacidad_asientos']) * 100, 1)

            total_estimado += pasajes_est
            total_capacidad += v['capacidad_asientos']

            nombre_ruta = f"{v['origen']} ➔ {v['destino']}"
            dia_idx = int(v['dia_semana_num']) # 0 (Lunes) a 6 (Domingo)

            if nombre_ruta not in rutas_semana:
                rutas_semana[nombre_ruta] = [0] * 7
                conteo_rutas_semana[nombre_ruta] = [0] * 7

            rutas_semana[nombre_ruta][dia_idx] += pct_ocupacion
            conteo_rutas_semana[nombre_ruta][dia_idx] += 1

        # Promediar los porcentajes por día de la semana
        datos_grafico = {}
        for ruta, acumulado in rutas_semana.items():
            datos_grafico[ruta] = []
            for i in range(7):
                cant = conteo_rutas_semana[ruta][i]
                prom = round(acumulado[i] / cant, 1) if cant > 0 else 0
                datos_grafico[ruta].append(prom)

        promedio_global = round((total_estimado / total_capacidad * 100), 1) if total_capacidad > 0 else 0

        return render_template(
            'admin/predicciones.html',
            datos_grafico_json=json.dumps(datos_grafico),
            promedio_ocupacion=promedio_global,
            total_viajes=len(viajes)
        )

    except Exception as e:
        return f"Error interno: {e}", 500