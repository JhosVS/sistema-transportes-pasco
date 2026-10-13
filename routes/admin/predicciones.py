# routes/admin/predicciones.py
import os
import json
import joblib
import pandas as pd
from flask import Blueprint, render_template
from models import db, ProgramacionViaje

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
        viajes = ProgramacionViaje.query.limit(200).all()

        rutas_semana = {}
        conteo_rutas_semana = {}

        total_estimado = 0
        total_capacidad = 0

        for v in viajes:
            fecha = v.fecha_salida
            horario = v.horario
            ruta = horario.ruta if horario else None
            vehiculo = v.vehiculo or (horario.vehiculo_default if horario else None)

            if not (horario and ruta and vehiculo):
                continue

            dia_semana_num = fecha.weekday()  # 0 (Lunes) a 6 (Domingo)
            mes = fecha.month
            dia_mes = fecha.day
            es_fin_semana = 1 if dia_semana_num in (4, 5, 6) else 0

            hora_salida = horario.hora_salida
            hora_salida_decimal = hora_salida.hour + hora_salida.minute / 60.0 + hora_salida.second / 3600.0 if hora_salida else 0.0

            capacidad_asientos = vehiculo.capacidad_asientos or 40
            precio_base = float(horario.precio_pasaje_base or 0.0)

            df_input = pd.DataFrame([{
                'dia_semana_num': int(dia_semana_num),
                'mes': int(mes),
                'dia_mes': int(dia_mes),
                'es_fin_semana': int(es_fin_semana),
                'id_ruta': int(ruta.id_ruta),
                'id_sede_origen': int(ruta.id_sede_origen),
                'id_sede_destino': int(ruta.id_sede_destino),
                'hora_salida_decimal': float(hora_salida_decimal),
                'precio_pasaje_base': float(precio_base),
                'capacidad_asientos': int(capacidad_asientos)
            }])

            prediccion_raw = modelo.predict(df_input)[0]
            pasajes_est = max(0, min(capacidad_asientos, int(round(prediccion_raw))))
            pct_ocupacion = round((pasajes_est / capacidad_asientos) * 100, 1)

            total_estimado += pasajes_est
            total_capacidad += capacidad_asientos

            origen_nombre = ruta.origen.nombre_sede if ruta.origen else "Origen"
            destino_nombre = ruta.destino.nombre_sede if ruta.destino else "Destino"
            nombre_ruta = f"{origen_nombre} ➔ {destino_nombre}"

            if nombre_ruta not in rutas_semana:
                rutas_semana[nombre_ruta] = [0] * 7
                conteo_rutas_semana[nombre_ruta] = [0] * 7

            rutas_semana[nombre_ruta][dia_semana_num] += pct_ocupacion
            conteo_rutas_semana[nombre_ruta][dia_semana_num] += 1

        # Promediar porcentajes por día
        datos_grafico = {}
        for ruta_nombre, acumulado in rutas_semana.items():
            datos_grafico[ruta_nombre] = []
            for i in range(7):
                cant = conteo_rutas_semana[ruta_nombre][i]
                prom = round(acumulado[i] / cant, 1) if cant > 0 else 0
                datos_grafico[ruta_nombre].append(prom)

        promedio_global = round((total_estimado / total_capacidad * 100), 1) if total_capacidad > 0 else 0

        return render_template(
            'admin/predicciones.html',
            datos_grafico_json=json.dumps(datos_grafico),
            promedio_ocupacion=promedio_global,
            total_viajes=len(viajes)
        )

    except Exception as e:
        return f"Error interno: {e}", 500