# routes/reservas.py
from datetime import datetime
import math
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from models import db, Cliente, ProgramacionViaje, ReservaVenta, DetallePasaje
from routes.utils.reniec import obtener_datos_dni

reservas_bp = Blueprint('reservas', __name__, url_prefix='/reserva')


# ============================================================
# API AJAX: CONSULTA RENIEC DE DNI
# ============================================================
@reservas_bp.route('/api/dni/<dni>', methods=['GET'])
def api_dni(dni):
    return jsonify(obtener_datos_dni(dni))


# ============================================================
# PASO 1: DATOS DEL COMPRADOR / CLIENTE
# ============================================================
@reservas_bp.route('/viaje/<int:id_viaje>/cliente', methods=['GET', 'POST'])
def cliente(id_viaje):
    viaje_obj = db.session.get(ProgramacionViaje, id_viaje)

    if not viaje_obj:
        flash('El viaje seleccionado no se encuentra disponible.', 'warning')
        return redirect(url_for('public.buscar_viaje'))

    horario = viaje_obj.horario
    ruta = horario.ruta if horario else None
    
    viaje = {
        'id_viaje': viaje_obj.id_viaje,
        'fecha_salida': viaje_obj.fecha_salida,
        'hora_salida': viaje_obj.salida_programada.strftime('%H:%M') if viaje_obj.salida_programada else (horario.hora_salida.strftime('%H:%M') if horario and horario.hora_salida else ''),
        'precio_pasaje_base': float(viaje_obj.precio_pasaje),
        'origen': ruta.origen.nombre_sede if ruta and ruta.origen else '',
        'origen_ciudad': ruta.origen.ciudad if ruta and ruta.origen else '',
        'destino': ruta.destino.nombre_sede if ruta and ruta.destino else '',
        'destino_ciudad': ruta.destino.ciudad if ruta and ruta.destino else ''
    }

    if request.method == 'POST':
        dni = request.form.get('num_documento', '').strip()
        nombres = request.form.get('nombres_razon_social', '').strip()
        fecha_nac_str = request.form.get('fecha_nacimiento', '').strip()
        sexo = request.form.get('sexo', '').strip() or None
        telefono = request.form.get('telefono', '').strip()
        email = request.form.get('email', '').strip()

        try:
            fecha_nacimiento = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date() if fecha_nac_str else None
        except ValueError:
            fecha_nacimiento = None

        # Registrar o actualizar cliente según la restricción UNIQUE(tipo_doc, num_documento)
        cliente_obj = Cliente.query.filter_by(tipo_doc='DNI', num_documento=dni).first()

        if cliente_obj:
            cliente_obj.nombres_razon_social = nombres
            cliente_obj.fecha_nacimiento = fecha_nacimiento
            cliente_obj.sexo = sexo
            cliente_obj.telefono = telefono
            cliente_obj.email = email
        else:
            cliente_obj = Cliente(
                tipo_doc='DNI',
                num_documento=dni,
                nombres_razon_social=nombres,
                fecha_nacimiento=fecha_nacimiento,
                sexo=sexo,
                telefono=telefono,
                email=email
            )
            db.session.add(cliente_obj)

        try:
            db.session.commit()
            session['reserva_temp'] = {
                'id_viaje': id_viaje,
                'id_cliente': cliente_obj.id_cliente,
                'dni': dni,
                'nombre_cliente': nombres,
                'fecha_nacimiento': fecha_nac_str,
                'sexo': sexo,
                'telefono': telefono
            }
            return redirect(url_for('reservas.asientos', id_viaje=id_viaje))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar la información del cliente: {e}', 'danger')

    return render_template('public/paso1_cliente.html', viaje=viaje)


# ============================================================
# PASO 2: SELECCIÓN DE ASIENTOS Y PROCESAMIENTO DE RESERVA
# ============================================================
@reservas_bp.route('/viaje/<int:id_viaje>/asientos', methods=['GET', 'POST'])
def asientos(id_viaje):
    reserva_temp = session.get('reserva_temp')
    if not reserva_temp or reserva_temp.get('id_viaje') != id_viaje:
        flash('Por favor ingrese sus datos antes de seleccionar los asientos.', 'info')
        return redirect(url_for('reservas.cliente', id_viaje=id_viaje))

    viaje_obj = db.session.get(ProgramacionViaje, id_viaje)
    if not viaje_obj:
        flash('El viaje no se encuentra disponible.', 'warning')
        return redirect(url_for('public.buscar_viaje'))

    horario = viaje_obj.horario
    ruta = horario.ruta if horario else None
    vehiculo = viaje_obj.vehiculo_efectivo

    capacidad_asientos = vehiculo.capacidad_asientos if vehiculo else 40
    
    # Asientos activos (ocupados)
    ocupados = [p.numero_asiento for p in viaje_obj.pasajes_activos]

    viaje = {
        'id_viaje': viaje_obj.id_viaje,
        'fecha_salida': viaje_obj.fecha_salida,
        'hora_salida': viaje_obj.salida_programada.strftime('%H:%M') if viaje_obj.salida_programada else (horario.hora_salida.strftime('%H:%M') if horario and horario.hora_salida else ''),
        'precio_pasaje_base': float(viaje_obj.precio_pasaje),
        'capacidad_asientos': capacidad_asientos,
        'placa': vehiculo.placa if vehiculo else 'N/A',
        'marca': vehiculo.marca if vehiculo else '',
        'modelo': vehiculo.modelo if vehiculo else '',
        'origen': ruta.origen.nombre_sede if ruta and ruta.origen else '',
        'origen_ciudad': ruta.origen.ciudad if ruta and ruta.origen else '',
        'destino': ruta.destino.nombre_sede if ruta and ruta.destino else '',
        'destino_ciudad': ruta.destino.ciudad if ruta and ruta.destino else ''
    }

    if request.method == 'POST':
        asientos_seleccionados = request.form.get('asientos_seleccionados', '').strip()
        if not asientos_seleccionados:
            flash('Debe seleccionar al menos un asiento.', 'warning')
            return redirect(url_for('reservas.asientos', id_viaje=id_viaje))

        lista_asientos = [int(a) for a in asientos_seleccionados.split(',') if a.isdigit()]

        # Validación anti-sobreventa (Overbooking)
        if any(a in ocupados for a in lista_asientos):
            flash('Uno o más asientos seleccionados ya han sido ocupados por otro comprador. Por favor elija otros.', 'danger')
            return redirect(url_for('reservas.asientos', id_viaje=id_viaje))

        monto_total = len(lista_asientos) * float(viaje_obj.precio_pasaje)

        try:
            # 1. Crear Venta / Reserva
            nueva_reserva = ReservaVenta(
                id_cliente=reserva_temp['id_cliente'],
                monto_total=monto_total,
                metodo_pago='efectivo',
                canal_venta='web',
                tipo_comprobante='boleta',
                estado='pagada'
            )
            db.session.add(nueva_reserva)
            db.session.flush()

            # Parsear fecha de nacimiento si existe
            fecha_nac_str = reserva_temp.get('fecha_nacimiento')
            try:
                fecha_nacimiento = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date() if fecha_nac_str else None
            except ValueError:
                fecha_nacimiento = None

            sexo = reserva_temp.get('sexo')

            # 2. Registrar Detalle de Pasajes (persistiendo sexo y fecha_nacimiento para la vista ML v_ventas)
            for num_asiento in lista_asientos:
                detalle = DetallePasaje(
                    id_reserva=nueva_reserva.id_reserva,
                    id_viaje=id_viaje,
                    numero_asiento=num_asiento,
                    dni_pasajero=reserva_temp['dni'],
                    nombre_pasajero=reserva_temp['nombre_cliente'],
                    fecha_nacimiento=fecha_nacimiento,
                    sexo=sexo,
                    precio_pagado=viaje_obj.precio_pasaje,
                    estado='vendido'
                )
                db.session.add(detalle)

            db.session.commit()
            id_reserva_creada = nueva_reserva.id_reserva
            session.pop('reserva_temp', None)

            return redirect(url_for('reservas.comprobante', id_reserva=id_reserva_creada))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar la compra: {e}', 'danger')

    num_filas = math.ceil(capacidad_asientos / 4)

    return render_template(
        'public/paso2_asientos.html',
        viaje=viaje,
        ocupados=ocupados,
        num_filas=num_filas,
        cliente=reserva_temp
    )


# ============================================================
# PASO 3: COMPROBANTE DE COMPRA Y RESUMEN
# ============================================================
@reservas_bp.route('/comprobante/<int:id_reserva>')
def comprobante(id_reserva):
    reserva_obj = db.session.get(ReservaVenta, id_reserva)

    if not reserva_obj:
        flash('Reserva no encontrada.', 'warning')
        return redirect(url_for('public.buscar_viaje'))

    cliente_obj = reserva_obj.cliente
    reserva = {
        'id_reserva': reserva_obj.id_reserva,
        'monto_total': float(reserva_obj.monto_total),
        'fecha_emision': reserva_obj.fecha_emision,
        'tipo_comprobante': reserva_obj.tipo_comprobante,
        'metodo_pago': reserva_obj.metodo_pago,
        'nombres_razon_social': cliente_obj.nombres_razon_social if cliente_obj else '',
        'num_documento': cliente_obj.num_documento if cliente_obj else '',
        'telefono': cliente_obj.telefono if cliente_obj else '',
        'email': cliente_obj.email if cliente_obj else ''
    }

    detalles = []
    for dp in reserva_obj.pasajes:
        viaje = dp.viaje
        horario = viaje.horario if viaje else None
        ruta = horario.ruta if horario else None
        vehiculo = viaje.vehiculo_efectivo if viaje else None

        detalles.append({
            'numero_asiento': dp.numero_asiento,
            'dni_pasajero': dp.dni_pasajero,
            'nombre_pasajero': dp.nombre_pasajero,
            'fecha_nacimiento': dp.fecha_nacimiento,
            'sexo': dp.sexo,
            'precio_pagado': float(dp.precio_pagado),
            'fecha_salida': viaje.fecha_salida if viaje else None,
            'hora_salida': viaje.salida_programada.strftime('%H:%M') if viaje and viaje.salida_programada else (horario.hora_salida.strftime('%H:%M') if horario and horario.hora_salida else ''),
            'origen': ruta.origen.nombre_sede if ruta and ruta.origen else '',
            'origen_ciudad': ruta.origen.ciudad if ruta and ruta.origen else '',
            'destino': ruta.destino.nombre_sede if ruta and ruta.destino else '',
            'destino_ciudad': ruta.destino.ciudad if ruta and ruta.destino else '',
            'placa': vehiculo.placa if vehiculo else '',
            'marca': vehiculo.marca if vehiculo else ''
        })

    return render_template('public/comprobante.html', reserva=reserva, detalles=detalles)