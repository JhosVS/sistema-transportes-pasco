# routes/public/encomiendas.py
import secrets
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy import func

from models import db, Cliente, ProgramacionViaje, ReservaVenta, DetalleEncomienda

encomiendas_bp = Blueprint('encomiendas', __name__, url_prefix='/encomienda')

# ---- Reglas de negocio (ajustables) ----
PESO_MIN_KG = Decimal('0.1')
PESO_MAX_KG = Decimal('50')
COBRO_MINIMO = Decimal('5.00')
ALFABETO_CLAVE = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # sin 0/O/1/I
LONGITUD_CLAVE = 6


# ============================================================
# HELPERS
# ============================================================
def _generar_clave(dni_destinatario):
    """Clave aleatoria que no se repita para el mismo DNI destinatario."""
    while True:
        clave = ''.join(secrets.choice(ALFABETO_CLAVE) for _ in range(LONGITUD_CLAVE))
        existe = DetalleEncomienda.query.filter_by(
            dni_destinatario=dni_destinatario, clave_recojo=clave
        ).first()
        if not existe:
            return clave


def _calcular_monto(peso, precio_kg):
    monto = (peso * precio_kg).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return max(monto, COBRO_MINIMO)


def _viaje_aceptando_carga(viaje_obj):
    return (
        viaje_obj is not None
        and viaje_obj.estado_viaje == 'Programado'
        and viaje_obj.salida_programada > datetime.now()
    )


def _resumen_viaje(viaje_obj):
    horario = viaje_obj.horario
    ruta = horario.ruta if horario else None
    return {
        'id_viaje': viaje_obj.id_viaje,
        'fecha_salida': viaje_obj.fecha_salida,
        'hora_salida': viaje_obj.salida_programada.strftime('%H:%M') if viaje_obj.salida_programada else '',
        'origen': ruta.origen.nombre_sede if ruta and ruta.origen else '',
        'origen_ciudad': ruta.origen.ciudad if ruta and ruta.origen else '',
        'destino': ruta.destino.nombre_sede if ruta and ruta.destino else '',
        'destino_ciudad': ruta.destino.ciudad if ruta and ruta.destino else '',
        'precio_kg': float(horario.precio_kg_carga_base) if horario else 0.0,
    }


def _kg_comprometidos(id_viaje):
    total = db.session.query(func.coalesce(func.sum(DetalleEncomienda.peso_kg), 0)).filter(
        DetalleEncomienda.id_viaje == id_viaje,
        DetalleEncomienda.estado_entrega != 'Perdido'
    ).scalar()
    return Decimal(total)


# ============================================================
# PASO 1: DATOS DEL REMITENTE (quien envía y paga)
# ============================================================
@encomiendas_bp.route('/viaje/<int:id_viaje>/remitente', methods=['GET', 'POST'])
def remitente(id_viaje):
    viaje_obj = db.session.get(ProgramacionViaje, id_viaje)
    if not _viaje_aceptando_carga(viaje_obj):
        flash('Este viaje ya no admite encomiendas. Elija otra salida.', 'warning')
        return redirect(url_for('public.buscar_viaje'))

    if request.method == 'POST':
        dni = request.form.get('num_documento', '').strip()
        nombres = request.form.get('nombres_razon_social', '').strip()
        fecha_nac_str = request.form.get('fecha_nacimiento', '').strip()
        sexo = request.form.get('sexo', '').strip() or None
        telefono = request.form.get('telefono', '').strip()
        email = request.form.get('email', '').strip()

        if len(dni) != 8 or not dni.isdigit() or not nombres:
            flash('Ingrese un DNI válido de 8 dígitos y el nombre completo.', 'warning')
            return render_template('public/paso1_cliente.html', viaje=_resumen_viaje(viaje_obj),
                                   titulo_paso='Paso 1: Datos del Remitente',
                                   texto_boton='Continuar a la Encomienda')

        try:
            fecha_nacimiento = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date() if fecha_nac_str else None
        except ValueError:
            fecha_nacimiento = None

        cliente_obj = Cliente.query.filter_by(tipo_doc='DNI', num_documento=dni).first()
        if cliente_obj:
            cliente_obj.nombres_razon_social = nombres
            cliente_obj.fecha_nacimiento = fecha_nacimiento
            cliente_obj.sexo = sexo
            cliente_obj.telefono = telefono
            cliente_obj.email = email
        else:
            cliente_obj = Cliente(
                tipo_doc='DNI', num_documento=dni, nombres_razon_social=nombres,
                fecha_nacimiento=fecha_nacimiento, sexo=sexo, telefono=telefono, email=email
            )
            db.session.add(cliente_obj)

        try:
            db.session.commit()
            session['encomienda_temp'] = {
                'id_viaje': id_viaje,
                'id_cliente': cliente_obj.id_cliente,
                'nombre_remitente': nombres,
                'dni_remitente': dni,
            }
            return redirect(url_for('encomiendas.paquete', id_viaje=id_viaje))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar los datos del remitente: {e}', 'danger')

    return render_template('public/paso1_cliente.html', viaje=_resumen_viaje(viaje_obj),
                           titulo_paso='Paso 1: Datos del Remitente',
                           texto_boton='Continuar a la Encomienda')


# ============================================================
# PASO 2: DESTINATARIO + PAQUETE
# ============================================================
@encomiendas_bp.route('/viaje/<int:id_viaje>/paquete', methods=['GET', 'POST'])
def paquete(id_viaje):
    temp = session.get('encomienda_temp')
    if not temp or temp.get('id_viaje') != id_viaje:
        flash('Primero ingrese los datos del remitente.', 'info')
        return redirect(url_for('encomiendas.remitente', id_viaje=id_viaje))

    viaje_obj = db.session.get(ProgramacionViaje, id_viaje)
    if not _viaje_aceptando_carga(viaje_obj):
        flash('Este viaje ya no admite encomiendas. Elija otra salida.', 'warning')
        return redirect(url_for('public.buscar_viaje'))

    viaje = _resumen_viaje(viaje_obj)

    if request.method == 'POST':
        dni_dest = request.form.get('dni_destinatario', '').strip()
        nombre_dest = request.form.get('nombre_destinatario', '').strip()
        tel_dest = request.form.get('telefono_destinatario', '').strip()
        descripcion = request.form.get('descripcion_contenido', '').strip()
        peso_str = request.form.get('peso_kg', '').strip().replace(',', '.')

        errores = []
        if len(dni_dest) != 8 or not dni_dest.isdigit():
            errores.append('El DNI del destinatario debe tener 8 dígitos.')
        if not nombre_dest:
            errores.append('Ingrese el nombre del destinatario.')
        if not tel_dest:
            errores.append('Ingrese el teléfono del destinatario.')
        if not descripcion:
            errores.append('Describa el contenido del paquete.')

        try:
            peso = Decimal(peso_str)
            if peso < PESO_MIN_KG or peso > PESO_MAX_KG:
                errores.append(f'El peso debe estar entre {PESO_MIN_KG} y {PESO_MAX_KG} kg.')
        except InvalidOperation:
            peso = None
            errores.append('Ingrese un peso válido en kg.')

        # Capacidad de carga del vehículo
        vehiculo = viaje_obj.vehiculo_efectivo
        if peso is not None and vehiculo and not errores:
            disponible = Decimal(vehiculo.capacidad_carga_kg) - _kg_comprometidos(id_viaje)
            if peso > disponible:
                errores.append(
                    f'No hay capacidad de carga suficiente en este viaje '
                    f'(disponible: {max(disponible, Decimal(0)):.2f} kg).'
                )

        if errores:
            for e in errores:
                flash(e, 'warning')
            return render_template('public/encomienda_paquete.html', viaje=viaje, remitente=temp,
                                   cobro_minimo=float(COBRO_MINIMO), peso_max=float(PESO_MAX_KG),
                                   form=request.form)

        precio_kg = Decimal(viaje_obj.horario.precio_kg_carga_base)
        monto = _calcular_monto(peso, precio_kg)

        try:
            reserva = ReservaVenta(
                id_cliente=temp['id_cliente'],
                monto_total=monto,
                metodo_pago='efectivo',
                canal_venta='web',
                tipo_comprobante='boleta',
                estado='pagada'
            )
            db.session.add(reserva)
            db.session.flush()

            encomienda = DetalleEncomienda(
                id_reserva=reserva.id_reserva,
                id_viaje=id_viaje,
                dni_destinatario=dni_dest,
                nombre_destinatario=nombre_dest,
                telefono_destinatario=tel_dest,
                descripcion_contenido=descripcion,
                peso_kg=peso,
                clave_recojo=_generar_clave(dni_dest),
                estado_entrega='Registrado',
                precio_pagado=monto
            )
            db.session.add(encomienda)
            db.session.commit()

            # Solo quien registró la encomienda en esta sesión puede ver el comprobante (contiene la clave)
            session['encomiendas_emitidas'] = session.get('encomiendas_emitidas', []) + [encomienda.id_detalle_encomienda]
            session.pop('encomienda_temp', None)
            return redirect(url_for('encomiendas.comprobante', id_encomienda=encomienda.id_detalle_encomienda))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar la encomienda: {e}', 'danger')

    return render_template('public/encomienda_paquete.html', viaje=viaje, remitente=temp,
                           cobro_minimo=float(COBRO_MINIMO), peso_max=float(PESO_MAX_KG), form={})


# ============================================================
# PASO 3: COMPROBANTE
# ============================================================
@encomiendas_bp.route('/comprobante/<int:id_encomienda>')
def comprobante(id_encomienda):
    if id_encomienda not in session.get('encomiendas_emitidas', []):
        flash('Para consultar su encomienda use su DNI de destinatario y la clave de recojo.', 'info')
        return redirect(url_for('encomiendas.seguimiento'))

    enc = db.session.get(DetalleEncomienda, id_encomienda)
    if not enc:
        flash('Encomienda no encontrada.', 'warning')
        return redirect(url_for('public.buscar_viaje'))

    reserva = enc.reserva
    cliente_obj = reserva.cliente
    viaje = _resumen_viaje(enc.viaje)

    datos = {
        'id_encomienda': enc.id_detalle_encomienda,
        'fecha_emision': reserva.fecha_emision,
        'metodo_pago': reserva.metodo_pago,
        'remitente': cliente_obj.nombres_razon_social if cliente_obj else '',
        'dni_remitente': cliente_obj.num_documento if cliente_obj else '',
        'dni_destinatario': enc.dni_destinatario,
        'nombre_destinatario': enc.nombre_destinatario,
        'telefono_destinatario': enc.telefono_destinatario,
        'descripcion': enc.descripcion_contenido,
        'peso_kg': float(enc.peso_kg),
        'clave_recojo': enc.clave_recojo,
        'estado': enc.estado_entrega,
        'monto': float(enc.precio_pagado),
    }
    return render_template('public/encomienda_comprobante.html', e=datos, viaje=viaje)


# ============================================================
# SEGUIMIENTO PÚBLICO (DNI destinatario + clave)
# ============================================================
@encomiendas_bp.route('/seguimiento', methods=['GET', 'POST'])
def seguimiento():
    resultados = None
    dni = ''
    clave = ''

    if request.method == 'POST':
        dni = request.form.get('dni_destinatario', '').strip()
        clave = request.form.get('clave_recojo', '').strip().upper()

        encomiendas = DetalleEncomienda.query.filter_by(
            dni_destinatario=dni, clave_recojo=clave
        ).all() if dni and clave else []

        if not encomiendas:
            flash('No encontramos una encomienda con esos datos. Verifique el DNI y la clave.', 'warning')
        else:
            resultados = []
            for enc in encomiendas:
                v = _resumen_viaje(enc.viaje)
                resultados.append({
                    'estado': enc.estado_entrega,
                    'peso_kg': float(enc.peso_kg),
                    'nombre_destinatario': enc.nombre_destinatario,
                    'origen': v['origen_ciudad'] or v['origen'],
                    'destino': v['destino_ciudad'] or v['destino'],
                    'fecha_salida': v['fecha_salida'],
                    'hora_salida': v['hora_salida'],
                    'entregado_en': enc.entregado_en,
                })

    return render_template('public/encomienda_seguimiento.html',
                           resultados=resultados, dni=dni, clave=clave)