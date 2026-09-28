# routes/public/main.py
from flask import Blueprint, render_template, request, flash
from database.db import get_connection
from datetime import datetime, timedelta

public_bp = Blueprint('public', __name__)

DIAS_PYTHON_A_DB = {0: 'Lunes', 1: 'Martes', 2: 'Miercoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sabado', 6: 'Domingo'}
DIAS_DB_A_PYTHON = {v: k for k, v in DIAS_PYTHON_A_DB.items()}

@public_bp.route('/')
def home():
    return render_template('public/index.html')

@public_bp.route('/buscar', methods=['GET', 'POST'])
def buscar_viaje():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM sedes ORDER BY nombre_sede ASC")
    sedes = cursor.fetchall()

    # Obtener relaciones de rutas activas (Origen -> Destino)
    cursor.execute("SELECT id_sede_origen, id_sede_destino FROM rutas")
    rutas_db = cursor.fetchall()

    viajes_disponibles = []
    origen_sel = request.form.get('id_origen')
    destino_sel = request.form.get('id_destino')

    if request.method == 'POST' and origen_sel and destino_sel:
        origen_sel, destino_sel = int(origen_sel), int(destino_sel)

        cursor.execute("""
            SELECT h.*, r.duracion_estimada_hrs, v.capacidad_asientos, v.placa, v.marca, v.modelo,
                   c.nombres AS conductor_nombre, c.apellidos AS conductor_apellido
            FROM horarios h
            INNER JOIN rutas r ON h.id_ruta = r.id_ruta
            INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
            INNER JOIN conductor c ON h.id_conductor = c.id_conductor
            WHERE r.id_sede_origen = %s AND r.id_sede_destino = %s AND h.estado = 'Activo'
        """, (origen_sel, destino_sel))
        horarios = cursor.fetchall()

        if not horarios:
            flash('No hay salidas disponibles para este trayecto.', 'info')
        else:
            ahora = datetime.now()
            fecha_hoy, hora_actual = ahora.date(), ahora.time()

            for h in horarios:
                dia_num = DIAS_DB_A_PYTHON[h['dia_semana']]
                dias_falta = (dia_num - fecha_hoy.weekday()) % 7
                fecha_proximo = fecha_hoy + timedelta(days=dias_falta)

                hora_salida_obj = (datetime.min + h['hora_salida']).time() if isinstance(h['hora_salida'], timedelta) else h['hora_salida']

                if fecha_proximo == fecha_hoy and hora_salida_obj <= hora_actual:
                    fecha_proximo += timedelta(days=7)

                cursor.execute("""
                    INSERT INTO programacion_viaje (id_horario, fecha_salida, estado_viaje)
                    VALUES (%s, %s, 'Programado')
                    ON DUPLICATE KEY UPDATE id_viaje = LAST_INSERT_ID(id_viaje)
                """, (h['id_horario'], fecha_proximo))
                conn.commit()

                cursor.execute("SELECT id_viaje FROM programacion_viaje WHERE id_horario = %s AND fecha_salida = %s", (h['id_horario'], fecha_proximo))
                id_viaje = cursor.fetchone()['id_viaje']

                cursor.execute("SELECT COUNT(*) AS ocupados FROM detalle_pasajes WHERE id_viaje = %s", (id_viaje,))
                ocupados = cursor.fetchone()['ocupados']

                viajes_disponibles.append({
                    'id_viaje': id_viaje,
                    'fecha_salida': fecha_proximo.strftime('%d/%m/%Y'),
                    'dia_nombre': h['dia_semana'],
                    'hora_salida': str(hora_salida_obj)[:5],
                    'precio': h['precio_pasaje_base'],
                    'duracion': h['duracion_estimada_hrs'],
                    'placa': h['placa'],
                    'bus': f"{h['marca']} {h['modelo']}",
                    'conductor': f"{h['conductor_nombre']} {h['conductor_apellido']}",
                    'asientos_libres': h['capacidad_asientos'] - ocupados
                })

            viajes_disponibles.sort(key=lambda x: datetime.strptime(x['fecha_salida'], '%d/%m/%Y'))

    cursor.close()
    conn.close()

    return render_template(
        'public/buscar_viaje.html',
        sedes=sedes,
        rutas_json=rutas_db,
        viajes=viajes_disponibles,
        origen_sel=origen_sel,
        destino_sel=destino_sel
    )