from datetime import datetime
import math

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from models import Cliente, DetallePasaje, ReservaVenta, db
from routes.utils.reniec import obtener_datos_dni
from routes.utils.salidas import crear_viaje, resolver

reservas_bp = Blueprint('reservas', __name__, url_prefix='/reserva')

MAX_ASIENTOS = 6
METODOS_PAGO = [('yape', 'Yape'), ('plin', 'Plin'), ('tarjeta', 'Tarjeta'), ('transferencia', 'Transferencia')]


@reservas_bp.route('/api/dni/<dni>')
def api_dni(dni):
    return jsonify(obtener_datos_dni(dni))


def _temp(id_horario, fecha):
    t = session.get('reserva_temp')
    return t if t and t.get('h') == id_horario and t.get('f') == fecha and t.get('asientos') else None


def _fecha(txt):
    try:
        return datetime.strptime(txt, '%Y-%m-%d').date() if txt else None
    except ValueError:
        return None


# ---------------------------------------------------------------- PASO 2: asientos
@reservas_bp.route('/horario/<int:id_horario>/<fecha>/asientos', methods=['GET', 'POST'])
def asientos(id_horario, fecha):
    s = resolver(id_horario, fecha)
    if not s:
        return redirect(url_for('public.buscar_viaje'))
    info, ocupados = s.info(), s.ocupados()
    destino = dict(id_horario=id_horario, fecha=fecha)

    if request.method == 'POST':
        lista = sorted({int(a) for a in request.form.get('asientos', '').split(',') if a.isdigit()})
        if not lista:
            flash('Elige al menos un asiento.', 'warning')
        elif len(lista) > MAX_ASIENTOS:
            flash(f'Máximo {MAX_ASIENTOS} asientos por compra.', 'warning')
        elif any(a < 1 or a > info['capacidad'] for a in lista):
            flash('Asiento inválido.', 'danger')
        elif any(a in ocupados for a in lista):
            flash('Alguno de los asientos ya fue ocupado. Elige otros.', 'danger')
        else:
            previo = _temp(id_horario, fecha)
            session['reserva_temp'] = {'h': id_horario, 'f': fecha, 'asientos': lista,
                                       'pasajeros': previo.get('pasajeros', {}) if previo else {},
                                       'contacto': previo.get('contacto', {}) if previo else {}}
            return redirect(url_for('reservas.pasajeros', **destino))
        return redirect(url_for('reservas.asientos', **destino))

    previo = _temp(id_horario, fecha)
    return render_template('public/paso2_asientos.html', viaje=info, ocupados=ocupados,
                           num_filas=math.ceil(info['capacidad'] / 4), max_asientos=MAX_ASIENTOS,
                           elegidos=previo['asientos'] if previo else [])


# ---------------------------------------------------------------- PASO 3: pasajeros
@reservas_bp.route('/horario/<int:id_horario>/<fecha>/pasajeros', methods=['GET', 'POST'])
def pasajeros(id_horario, fecha):
    s = resolver(id_horario, fecha)
    if not s:
        return redirect(url_for('public.buscar_viaje'))
    destino = dict(id_horario=id_horario, fecha=fecha)
    temp = _temp(id_horario, fecha)
    if not temp:
        flash('Primero elige tus asientos.', 'info')
        return redirect(url_for('reservas.asientos', **destino))
    lista = temp['asientos']

    if request.method == 'POST':
        pax, errores, vistos = {}, [], set()
        for a in lista:
            dni = request.form.get(f'dni_{a}', '').strip()
            nombre = request.form.get(f'nombre_{a}', '').strip()
            if not (dni.isdigit() and len(dni) == 8):
                errores.append(f'Asiento {a}: el DNI debe tener 8 dígitos.')
            elif dni in vistos:
                errores.append(f'Asiento {a}: el DNI está repetido en otro asiento.')
            if not nombre:
                errores.append(f'Asiento {a}: falta el nombre.')
            vistos.add(dni)
            sexo = request.form.get(f'sexo_{a}', '').strip()
            pax[str(a)] = {'dni': dni, 'nombre': nombre, 'nac': request.form.get(f'nac_{a}', '').strip(),
                           'sexo': sexo if sexo in ('M', 'F', 'otro') else ''}
        contacto = {'telefono': request.form.get('telefono', '').strip(),
                    'email': request.form.get('email', '').strip()}
        if not contacto['telefono']:
            errores.append('Ingresa un teléfono de contacto.')
        if errores:
            for e in errores:
                flash(e, 'warning')
            datos = request.form
        else:
            temp.update(pasajeros=pax, contacto=contacto)
            session['reserva_temp'] = temp
            return redirect(url_for('reservas.pago', **destino))
    else:
        datos = {}
        for a, p in temp.get('pasajeros', {}).items():
            datos.update({f'dni_{a}': p['dni'], f'nombre_{a}': p['nombre'], f'nac_{a}': p['nac'],
                          f'sexo_{a}': p['sexo']})
        datos.update(temp.get('contacto', {}))

    return render_template('public/paso3_pasajeros.html', viaje=s.info(), asientos=lista, datos=datos)


# ---------------------------------------------------------------- PASO 4: pago (aquí se crea el viaje)
@reservas_bp.route('/horario/<int:id_horario>/<fecha>/pago', methods=['GET', 'POST'])
def pago(id_horario, fecha):
    s = resolver(id_horario, fecha)
    if not s:
        return redirect(url_for('public.buscar_viaje'))
    destino = dict(id_horario=id_horario, fecha=fecha)
    temp = _temp(id_horario, fecha)
    if not temp or not temp.get('pasajeros'):
        flash('Completa los datos de los pasajeros.', 'info')
        return redirect(url_for('reservas.pasajeros', **destino))
    info, lista = s.info(), temp['asientos']
    total = info['precio'] * len(lista)

    if request.method == 'POST':
        metodo = request.form.get('metodo', '')
        if metodo not in dict(METODOS_PAGO):
            flash('Elige un método de pago.', 'warning')
            return redirect(url_for('reservas.pago', **destino))
        try:
            v = crear_viaje(s)
            if v.estado_viaje != 'Programado':
                raise ValueError('El viaje ya no está disponible.')
            ocupado = (db.session.query(DetallePasaje)
                       .filter(DetallePasaje.id_viaje == v.id_viaje, DetallePasaje.estado != 'anulado',
                               DetallePasaje.numero_asiento.in_(lista)).count())
            if ocupado:
                db.session.rollback()
                flash('Alguno de los asientos fue ocupado mientras completabas la compra. Elige otros.', 'danger')
                return redirect(url_for('reservas.asientos', **destino))

            comp = temp['pasajeros'][str(lista[0])]       # el comprador es el pasajero del primer asiento
            cli = Cliente.query.filter_by(tipo_doc='DNI', num_documento=comp['dni']).first()
            if not cli:
                cli = Cliente(tipo_doc='DNI', num_documento=comp['dni'])
                db.session.add(cli)
            cli.nombres_razon_social = comp['nombre']
            cli.fecha_nacimiento = _fecha(comp['nac'])
            cli.sexo = comp['sexo'] or None
            cli.telefono = temp['contacto']['telefono']
            cli.email = temp['contacto']['email']
            db.session.flush()

            reserva = ReservaVenta(id_cliente=cli.id_cliente, monto_total=float(v.precio_pasaje) * len(lista),
                                   metodo_pago=metodo, canal_venta='web', tipo_comprobante='boleta',
                                   estado='pagada')
            db.session.add(reserva)
            db.session.flush()
            for a in lista:
                p = temp['pasajeros'][str(a)]
                db.session.add(DetallePasaje(
                    id_reserva=reserva.id_reserva, id_viaje=v.id_viaje, numero_asiento=a,
                    dni_pasajero=p['dni'], nombre_pasajero=p['nombre'],
                    fecha_nacimiento=_fecha(p['nac']), sexo=p['sexo'] or None,
                    precio_pagado=v.precio_pasaje, estado='vendido'))
            db.session.commit()
            id_reserva = reserva.id_reserva
            session.pop('reserva_temp', None)
            return redirect(url_for('reservas.comprobante', id_reserva=id_reserva))
        except IntegrityError:
            db.session.rollback()
            flash('Un asiento acaba de ser ocupado. Elige otros.', 'danger')
            return redirect(url_for('reservas.asientos', **destino))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar la compra: {e}', 'danger')

    filas = [{'asiento': a, **temp['pasajeros'][str(a)]} for a in lista]
    return render_template('public/paso4_pago.html', viaje=info, filas=filas, total=total,
                           contacto=temp['contacto'], metodos=METODOS_PAGO)


# ---------------------------------------------------------------- comprobante
@reservas_bp.route('/comprobante/<int:id_reserva>')
def comprobante(id_reserva):
    r = db.session.get(ReservaVenta, id_reserva)
    if not r:
        flash('Reserva no encontrada.', 'warning')
        return redirect(url_for('public.buscar_viaje'))
    c = r.cliente
    reserva = {'id_reserva': r.id_reserva, 'monto_total': float(r.monto_total),
               'fecha_emision': r.fecha_emision, 'metodo_pago': r.metodo_pago,
               'nombres_razon_social': c.nombres_razon_social if c else '',
               'num_documento': c.num_documento if c else ''}
    detalles = []
    for dp in sorted(r.pasajes, key=lambda x: x.numero_asiento):
        v = dp.viaje
        ruta = v.horario.ruta
        detalles.append({'numero_asiento': dp.numero_asiento, 'dni_pasajero': dp.dni_pasajero,
                         'nombre_pasajero': dp.nombre_pasajero, 'precio_pagado': float(dp.precio_pagado),
                         'fecha_salida': v.fecha_salida, 'hora_salida': v.salida_programada.strftime('%H:%M'),
                         'origen_ciudad': ruta.origen.ciudad, 'destino_ciudad': ruta.destino.ciudad,
                         'terminal': ruta.origen.nombre_sede})
    return render_template('public/comprobante.html', reserva=reserva, detalles=detalles)