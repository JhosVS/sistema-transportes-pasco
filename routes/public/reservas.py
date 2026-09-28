# routes/public/reservas.py
import math
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from database.db import get_connection
from routes.utils.reniec import obtener_datos_dni

reservas_bp = Blueprint('reservas', __name__, url_prefix='/reserva')

# Endpoint AJAX para consulta de DNI
@reservas_bp.route('/api/dni/<dni>', methods=['GET'])
def api_dni(dni):
    return jsonify(obtener_datos_dni(dni))


# Paso 1: Ingreso de Datos del Cliente
@reservas_bp.route('/viaje/<int:id_viaje>/cliente', methods=['GET', 'POST'])
def cliente(id_viaje):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Validar que el viaje exista
    cursor.execute("""
        SELECT pv.id_viaje, pv.fecha_salida, TIME_FORMAT(h.hora_salida, '%H:%i') as hora_salida,
               h.precio_pasaje_base, so.nombre_sede AS origen, sd.nombre_sede AS destino
        FROM programacion_viaje pv
        INNER JOIN horarios h ON pv.id_horario = h.id_horario
        INNER JOIN rutas r ON h.id_ruta = r.id_ruta
        INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
        INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
        WHERE pv.id_viaje = %s
    """, (id_viaje,))
    viaje = cursor.fetchone()

    if not viaje:
        flash('El viaje seleccionado no existe.', 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('public.buscar_viaje'))

    if request.method == 'POST':
        dni = request.form.get('num_documento').strip()
        nombres = request.form.get('nombres_razon_social').strip()
        telefono = request.form.get('telefono').strip()
        email = request.form.get('email').strip()

        # Guardar o actualizar en la tabla 'clientes'
        cursor.execute("SELECT id_cliente FROM clientes WHERE num_documento = %s", (dni,))
        cliente_existente = cursor.fetchone()

        if cliente_existente:
            id_cliente = cliente_existente['id_cliente']
            cursor.execute("""
                UPDATE clientes 
                SET nombres_razon_social = %s, telefono = %s, email = %s 
                WHERE id_cliente = %s
            """, (nombres, telefono, email, id_cliente))
        else:
            cursor.execute("""
                INSERT INTO clientes (num_documento, nombres_razon_social, telefono, email)
                VALUES (%s, %s, %s, %s)
            """, (dni, nombres, telefono, email))
            id_cliente = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()

        # Guardar cliente en sesión para el siguiente paso
        session['reserva_temp'] = {
            'id_viaje': id_viaje,
            'id_cliente': id_cliente,
            'dni': dni,
            'nombre_cliente': nombres,
            'telefono': telefono
        }

        return redirect(url_for('reservas.asientos', id_viaje=id_viaje))

    cursor.close()
    conn.close()
    return render_template('public/paso1_cliente.html', viaje=viaje)


# Paso 2: Selección de Asientos en la Matriz
@reservas_bp.route('/viaje/<int:id_viaje>/asientos', methods=['GET', 'POST'])
def asientos(id_viaje):
    reserva_temp = session.get('reserva_temp')
    if not reserva_temp or reserva_temp.get('id_viaje') != id_viaje:
        flash('Por favor ingrese sus datos antes de seleccionar asientos.', 'info')
        return redirect(url_for('reservas.cliente', id_viaje=id_viaje))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Detalle del viaje y capacidad del bus
    cursor.execute("""
        SELECT pv.id_viaje, pv.fecha_salida, TIME_FORMAT(h.hora_salida, '%H:%i') as hora_salida,
               h.precio_pasaje_base, v.capacidad_asientos, v.placa, v.marca, v.modelo,
               so.nombre_sede AS origen, sd.nombre_sede AS destino
        FROM programacion_viaje pv
        INNER JOIN horarios h ON pv.id_horario = h.id_horario
        INNER JOIN rutas r ON h.id_ruta = r.id_ruta
        INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
        INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
        INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
        WHERE pv.id_viaje = %s
    """, (id_viaje,))
    viaje = cursor.fetchone()

    # Asientos ya vendidos
    cursor.execute("SELECT numero_asiento FROM detalle_pasajes WHERE id_viaje = %s", (id_viaje,))
    ocupados = [row['numero_asiento'] for row in cursor.fetchall()]

    if request.method == 'POST':
        asientos_seleccionados = request.form.get('asientos_seleccionados') # Ej: "12,13"
        if not asientos_seleccionados:
            flash('Debe seleccionar al menos un asiento.', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('reservas.asientos', id_viaje=id_viaje))

        lista_asientos = [int(a) for a in asientos_seleccionados.split(',') if a.isdigit()]
        monto_total = len(lista_asientos) * float(viaje['precio_pasaje_base'])

        # 1. Crear Venta Cabecera (reservas_ventas)
        cursor.execute("""
            INSERT INTO reservas_ventas (id_cliente, monto_total, metodo_pago, tipo_comprobante)
            VALUES (%s, %s, 'Efectivo/Simulado', 'Boleta')
        """, (reserva_temp['id_cliente'], monto_total))
        id_reserva = cursor.lastrowid

        # 2. Registrar Detalle de Pasajes (detalle_pasajes)
        for num_asiento in lista_asientos:
            cursor.execute("""
                INSERT INTO detalle_pasajes (id_reserva, id_viaje, numero_asiento, dni_pasajero, nombre_pasajero, precio_pagado)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                id_reserva, id_viaje, num_asiento, 
                reserva_temp['dni'], reserva_temp['nombre_cliente'], viaje['precio_pasaje_base']
            ))

        conn.commit()
        cursor.close()
        conn.close()

        session.pop('reserva_temp', None)
        return redirect(url_for('reservas.comprobante', id_reserva=id_reserva))

    # Generar estructura de filas (4 asientos por fila)
    num_filas = math.ceil(viaje['capacidad_asientos'] / 4)
    
    cursor.close()
    conn.close()

    return render_template(
        'public/paso2_asientos.html',
        viaje=viaje,
        ocupados=ocupados,
        num_filas=num_filas,
        cliente=reserva_temp
    )


# Paso 3: Comprobante de Pago & Resumen de Reserva
@reservas_bp.route('/comprobante/<int:id_reserva>')
def comprobante(id_reserva):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT rv.*, c.nombres_razon_social, c.num_documento, c.telefono, c.email
        FROM reservas_ventas rv
        INNER JOIN clientes c ON rv.id_cliente = c.id_cliente
        WHERE rv.id_reserva = %s
    """, (id_reserva,))
    reserva = cursor.fetchone()

    if not reserva:
        flash('Reserva no encontrada.', 'warning')
        cursor.close()
        conn.close()
        return redirect(url_for('public.buscar_viaje'))

    cursor.execute("""
        SELECT dp.*, pv.fecha_salida, TIME_FORMAT(h.hora_salida, '%H:%i') as hora_salida,
               so.nombre_sede AS origen, sd.nombre_sede AS destino, v.placa, v.marca
        FROM detalle_pasajes dp
        INNER JOIN programacion_viaje pv ON dp.id_viaje = pv.id_viaje
        INNER JOIN horarios h ON pv.id_horario = h.id_horario
        INNER JOIN rutas r ON h.id_ruta = r.id_ruta
        INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
        INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
        INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
        WHERE dp.id_reserva = %s
    """, (id_reserva,))
    detalles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('public/comprobante.html', reserva=reserva, detalles=detalles)