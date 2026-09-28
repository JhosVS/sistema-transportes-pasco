# routes/admin/viajes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import get_connection

admin_viajes_bp = Blueprint('admin_viajes', __name__, url_prefix='/admin/horarios')

@admin_viajes_bp.route('/')
def index():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Listar todos los horarios definidos
    query = """
        SELECT 
            h.id_horario,
            h.dia_semana,
            TIME_FORMAT(h.hora_salida, '%H:%i') AS hora_salida,
            h.precio_pasaje_base,
            h.precio_kg_carga_base,
            h.estado,
            so.nombre_sede AS origen,
            sd.nombre_sede AS destino,
            v.placa,
            v.marca,
            CONCAT(c.nombres, ' ', c.apellidos) AS conductor
        FROM horarios h
        INNER JOIN rutas r ON h.id_ruta = r.id_ruta
        INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
        INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
        INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
        INNER JOIN conductor c ON h.id_conductor = c.id_conductor
        ORDER BY FIELD(h.dia_semana, 'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo'), h.hora_salida
    """
    cursor.execute(query)
    horarios = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('admin/viajes/index.html', horarios=horarios)


@admin_viajes_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_ruta = request.form['id_ruta']
        id_vehiculo = request.form['id_vehiculo']
        id_conductor = request.form['id_conductor']
        dia_semana = request.form['dia_semana']
        hora_salida = request.form['hora_salida']
        precio_pasaje_base = request.form['precio_pasaje_base']
        precio_kg_carga_base = request.form['precio_kg_carga_base']

        query_insert = """
            INSERT INTO horarios 
            (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Activo')
        """
        cursor.execute(query_insert, (
            id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base
        ))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Horario registrado con éxito', 'success')
        return redirect(url_for('admin_viajes.index'))

    # Obtener catálogos para el formulario
    cursor.execute("""
        SELECT r.id_ruta, CONCAT(so.nombre_sede, ' ➔ ', sd.nombre_sede) AS nombre_ruta 
        FROM rutas r
        INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
        INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
    """)
    rutas = cursor.fetchall()

    cursor.execute("SELECT id_vehiculo, CONCAT(placa, ' - ', marca, ' ', modelo) AS vehiculo FROM vehiculo WHERE estado = 'Disponible'")
    vehiculos = cursor.fetchall()

    cursor.execute("SELECT id_conductor, CONCAT(nombres, ' ', apellidos) AS conductor FROM conductor WHERE estado = 'Activo'")
    conductores = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/viajes/formulario.html', rutas=rutas, vehiculos=vehiculos, conductores=conductores)