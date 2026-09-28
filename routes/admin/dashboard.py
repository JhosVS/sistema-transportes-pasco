from flask import Blueprint, render_template, session, redirect, url_for
import mysql.connector

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Configuración directa de la conexión a MySQL
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',         # Cambia esto si tu usuario de MySQL es diferente
        password='',         # Coloca tu contraseña de MySQL aquí
        database='bd_transporte_pasco'
    )

@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # dictionary=True permite acceder a las columnas por nombre

    try:
        # 1. KPIs principales
        cursor.execute("SELECT COALESCE(SUM(monto_total), 0) AS ingresos FROM reservas_ventas")
        ingresos_totales = cursor.fetchone()['ingresos']

        cursor.execute("SELECT COUNT(*) AS total FROM detalle_pasajes")
        total_pasajes = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM vehiculo WHERE estado = 'Disponible'")
        buses_disponibles = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM vehiculo")
        total_buses = cursor.fetchone()['total']

        kpis = {
            'ingresos_mes': float(ingresos_totales),
            'total_pasajes_mes': total_pasajes,
            'buses_activos': buses_disponibles,
            'total_buses': total_buses,
            'ocupacion_promedio': 0  # Se calcula automáticamente si hay datos
        }

        # 2. Gráfico 1: Ventas por fecha
        cursor.execute("""
            SELECT DATE_FORMAT(fecha_emision, '%d %b') AS fecha, SUM(monto_total) AS total
            FROM reservas_ventas
            GROUP BY DATE(fecha_emision), DATE_FORMAT(fecha_emision, '%d %b')
            ORDER BY DATE(fecha_emision) ASC
            LIMIT 14
        """)
        ventas_db = cursor.fetchall()
        labels_ventas = [v['fecha'] for v in ventas_db] if ventas_db else ['Sin ventas']
        data_ventas = [float(v['total']) for v in ventas_db] if ventas_db else [0]

        # 3. Gráfico 2: Estado de la flota de buses
        cursor.execute("""
            SELECT estado, COUNT(*) AS cantidad
            FROM vehiculo
            GROUP BY estado
        """)
        flota_db = cursor.fetchall()
        labels_flota = [f['estado'] for f in flota_db] if flota_db else ['Sin buses']
        data_flota = [f['cantidad'] for f in flota_db] if flota_db else [0]

        # 4. Gráfico 3: Top Rutas con más pasajes vendidos (Corregido)
        cursor.execute("""
            SELECT 
                CONCAT(so.nombre_sede, ' ➔ ', sd.nombre_sede) AS ruta,
                COUNT(dp.id_detalle_pasaje) AS pasajes_vendidos
            FROM detalle_pasajes dp
            INNER JOIN programacion_viaje pv ON dp.id_viaje = pv.id_viaje
            INNER JOIN horarios h ON pv.id_horario = h.id_horario
            INNER JOIN rutas r ON h.id_ruta = r.id_ruta
            INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
            INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
            GROUP BY r.id_ruta, so.nombre_sede, sd.nombre_sede
            ORDER BY pasajes_vendidos DESC
            LIMIT 5
        """)
        rutas_db = cursor.fetchall()
        labels_rutas = [r['ruta'] for r in rutas_db] if rutas_db else ['Sin rutas registradas']
        data_rutas = [r['pasajes_vendidos'] for r in rutas_db] if rutas_db else [0]

    finally:
        cursor.close()
        conn.close()

    return render_template(
        'admin/dashboard.html',
        kpis=kpis,
        labels_ventas=labels_ventas,
        data_ventas=data_ventas,
        labels_flota=labels_flota,
        data_flota=data_flota,
        labels_rutas=labels_rutas,
        data_rutas=data_rutas
    )