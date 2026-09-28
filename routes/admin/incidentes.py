# routes/admin/incidentes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from database.db import get_connection

incidentes_bp = Blueprint('incidentes', __name__, url_prefix='/admin/incidentes')

# Listar todos los incidentes
@incidentes_bp.route('/')
def listar_incidentes():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT ir.*, pv.fecha_salida, TIME_FORMAT(h.hora_salida, '%H:%i') as hora_salida,
               so.nombre_sede AS origen, sd.nombre_sede AS destino,
               v.placa, v.marca, v.modelo,
               c.nombres AS conductor_nombre, c.apellidos AS conductor_apellido
        FROM incidentes_ruta ir
        INNER JOIN programacion_viaje pv ON ir.id_viaje = pv.id_viaje
        INNER JOIN horarios h ON pv.id_horario = h.id_horario
        INNER JOIN rutas r ON h.id_ruta = r.id_ruta
        INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
        INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
        INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
        INNER JOIN conductor c ON h.id_conductor = c.id_conductor
        ORDER BY ir.fecha_hora DESC
    """
    cursor.execute(query)
    incidentes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/incidentes/index.html', incidentes=incidentes)


# Formulario para registrar incidente
@incidentes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_incidente():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_viaje = request.form.get('id_viaje')
        tipo_incidente = request.form.get('tipo_incidente')
        lugar_referencial = request.form.get('lugar_referencial').strip()
        minutos_retraso = request.form.get('minutos_retraso_estimado', 0)
        descripcion = request.form.get('descripcion').strip()

        cursor.execute("""
            INSERT INTO incidentes_ruta (id_viaje, tipo_incidente, descripcion, lugar_referencial, minutos_retraso_estimado)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_viaje, tipo_incidente, descripcion, lugar_referencial, minutos_retraso))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Incidente registrado correctamente.', 'success')
        return redirect(url_for('incidentes.listar_incidentes'))

    # Cargar viajes activos o programados recientemente para el desplegable
    cursor.execute("""
        SELECT pv.id_viaje, pv.fecha_salida, TIME_FORMAT(h.hora_salida, '%H:%i') as hora_salida,
               so.nombre_sede AS origen, sd.nombre_sede AS destino, v.placa
        FROM programacion_viaje pv
        INNER JOIN horarios h ON pv.id_horario = h.id_horario
        INNER JOIN rutas r ON h.id_ruta = r.id_ruta
        INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
        INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
        INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
        ORDER BY pv.fecha_salida DESC
        LIMIT 20
    """)
    viajes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/incidentes/nuevo.html', viajes=viajes)