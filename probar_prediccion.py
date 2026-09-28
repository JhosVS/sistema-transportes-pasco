# probar_prediccion.py
import joblib
import pandas as pd

# 1. Cargar el modelo
modelo = joblib.load('modelo_demanda.joblib')

# 2. Datos exactos de una fila existente en tu CSV (Ejemplo: Fila de la Ruta 3)
# 37,2026-01-01,Thursday,3,1,1,0,3,1,3,6.0000,30.00,36,21
nuevo_viaje = pd.DataFrame([{
    'dia_semana_num': 3,        # Jueves
    'mes': 1,                   # Enero
    'dia_mes': 1,               # Día 1
    'es_fin_semana': 0,        # No es fin de semana
    'id_ruta': 3,               # Ruta ID 3
    'id_sede_origen': 1,       # Sede Origen 1
    'id_sede_destino': 3,      # Sede Destino 3
    'hora_salida_decimal': 6.0, # 6:00 AM
    'precio_pasaje_base': 30.0, # S/. 30.00
    'capacidad_asientos': 36    # Bus de 36 asientos
}])

# 3. Predicción
estimacion = modelo.predict(nuevo_viaje)[0]
asientos_est = max(0, int(round(estimacion)))

print("================ PREDICCIÓN CON DATOS REALES ================")
print(f"🎟️ Pasajes estimados a vender: {asientos_est} de 36")
print(f"📊 Ocupación proyectada: {round((asientos_est / 36) * 100, 1)}%")
print("=============================================================")