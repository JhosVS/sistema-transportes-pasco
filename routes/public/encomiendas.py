import secrets
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from models import Cliente, DetalleEncomienda, ReservaVenta, db
from routes.utils.salidas import Salida, crear_viaje, resolver

encomiendas_bp = Blueprint('encomiendas', __name__, url_prefix='/encomienda')

PESO_MIN, PESO_MAX = Decimal('1'), Decimal('20')   # kg por encomienda
ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
METODOS = [('yape', 'Yape'), ('plin', 'Plin'), ('tarjeta', 'Tarjeta'), ('transferencia', 'Transferencia')]
ETAPAS = ['Registrada', 'En tránsito', 'En agencia destino', 'Entregada']
AVISO = 'Este viaje ya no admite encomiendas. Elige otra salida.'


def _clave(dni):
    while True:
        c = ''.join(secrets.choice(ALFABETO) for _ in range(6))
        if not DetalleEncomienda.query.filter_by(dni_destinatario=dni, clave_recojo=c).first():
            return c


def _monto(peso, precio_kg):
    return (peso * precio_kg).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _carga_libre(s):
    """Kg que aún caben en el vehículo (None si no hay vehículo asignado)."""
    if not s.vehiculo:
        return None
    usado = 0
    if s.viaje:
        usado = db.session.query(func.coalesce(func.sum(DetalleEncomienda.peso_kg), 0)).filter(
            DetalleEncomienda.id_viaje == s.viaje.id_viaje,
            DetalleEncomienda.estado_entrega != 'Perdido').scalar()
    return max(Decimal(s.vehiculo.capacidad_carga_kg) - Decimal(usado), Decimal(0))


def _error_capacidad(s, peso):
    libre = _carga_libre(s)
    if libre is not None and peso > libre:
        return f'Este viaje solo admite {libre:.1f} kg más de carga.'
    return None


def _temp(id_horario, fecha):
    t = session.get('encomienda_temp')
    return t if t and t.get('h') == id_horario and t.get('f') == fecha else None


def _leer(form):
    d = {k: form.get(k, '').strip() for k in
         ('dni_rem', 'nombre_rem', 'tel_rem', 'dni_dest', 'nombre_dest', 'tel_dest', 'descripcion', 'peso')}
    err = []
    for k, quien in (('dni_rem', 'remitente'), ('dni_dest', 'destinatario')):
        if not (d[k].isdigit() and len(d[k]) == 8):
            err.append(f'El DNI del {quien} debe tener 8 dígitos.')
    for k, t in (('nombre_rem', 'nombre del remitente'), ('tel_rem', 'teléfono del remitente'),
                 ('nombre_dest', 'nombre del destinatario'), ('tel_dest', 'teléfono del destinatario'),
                 ('descripcion', 'contenido del paquete')):
        if not d[k]:
            err.append(f'Falta el {t}.')
    peso = None
    try:
        peso = Decimal(d['peso'].replace(',', '.'))
        if not PESO_MIN <= peso <= PESO_MAX:
            err.append(f'El peso debe estar entre {PESO_MIN:.0f} y {PESO_MAX:.0f} kg.')
        elif peso != peso.quantize(Decimal('0.1')):
            err.append('El peso admite un solo decimal (por ejemplo 1.5).')
    except InvalidOperation:
        err.append('Ingresa un peso válido en kg.')
    return d, err, peso


# ---------------------------------------------------------------- PASO 2: envío
@encomiendas_bp.route('/horario/<int:id_horario>/<fecha>/envio', methods=['GET', 'POST'])
def envio(id_horario, fecha):
    s = resolver(id_horario, fecha, AVISO)
    if not s:
        return redirect(url_for('public.buscar_viaje'))
    datos = {}
    if request.method == 'POST':
        datos, err, peso = _leer(request.form)
        if not err:
            e = _error_capacidad(s, peso)
            err = [e] if e else []
        if err:
            for e in err:
                flash(e, 'warning')
        else:
            session['encomienda_temp'] = {'h': id_horario, 'f': fecha, **datos}
            return redirect(url_for('encomiendas.pago', id_horario=id_horario, fecha=fecha))
    elif _temp(id_horario, fecha):
        datos = session['encomienda_temp']
    libre = _carga_libre(s)
    limite = PESO_MAX if libre is None else min(PESO_MAX, libre)
    if limite < PESO_MIN:
        flash('Este viaje ya no tiene capacidad de carga. Elige otra salida.', 'warning')
        return redirect(url_for('public.buscar_viaje'))
    return render_template('public/encomienda_envio.html', viaje=s.info(), datos=datos,
                           peso_min=float(PESO_MIN), limite=float(limite),
                           libre=None if libre is None else float(libre))


# ---------------------------------------------------------------- PASO 3: pago (aquí se crea el viaje)
@encomiendas_bp.route('/horario/<int:id_horario>/<fecha>/pago', methods=['GET', 'POST'])
def pago(id_horario, fecha):
    s = resolver(id_horario, fecha, AVISO)
    if not s:
        return redirect(url_for('public.buscar_viaje'))
    t = _temp(id_horario, fecha)
    if not t:
        return redirect(url_for('encomiendas.envio', id_horario=id_horario, fecha=fecha))

    peso = Decimal(t['peso'].replace(',', '.'))
    monto = _monto(peso, Decimal(s.h.precio_kg_carga_base))

    if request.method == 'POST':
        metodo = request.form.get('metodo', '')
        if metodo not in dict(METODOS):
            flash('Elige un método de pago.', 'warning')
        else:
            try:
                v = crear_viaje(s)
                if v.estado_viaje != 'Programado':
                    raise ValueError('El viaje ya no admite encomiendas.')
                err = _error_capacidad(s, peso)
                if err:
                    db.session.rollback()
                    flash(err, 'warning')
                    return redirect(url_for('encomiendas.envio', id_horario=id_horario, fecha=fecha))
                cli = Cliente.query.filter_by(tipo_doc='DNI', num_documento=t['dni_rem']).first()
                if not cli:
                    cli = Cliente(tipo_doc='DNI', num_documento=t['dni_rem'])
                    db.session.add(cli)
                cli.nombres_razon_social, cli.telefono = t['nombre_rem'], t['tel_rem']
                db.session.flush()
                reserva = ReservaVenta(id_cliente=cli.id_cliente, monto_total=monto, metodo_pago=metodo,
                                       canal_venta='web', tipo_comprobante='boleta', estado='pagada')
                db.session.add(reserva)
                db.session.flush()
                enc = DetalleEncomienda(
                    id_reserva=reserva.id_reserva, id_viaje=v.id_viaje, dni_destinatario=t['dni_dest'],
                    nombre_destinatario=t['nombre_dest'], telefono_destinatario=t['tel_dest'],
                    descripcion_contenido=t['descripcion'], peso_kg=peso, clave_recojo=_clave(t['dni_dest']),
                    estado_entrega='Registrado', precio_pagado=monto)
                db.session.add(enc)
                db.session.commit()
                session['encomiendas_emitidas'] = session.get('encomiendas_emitidas', []) + [enc.id_detalle_encomienda]
                session.pop('encomienda_temp', None)
                return redirect(url_for('encomiendas.comprobante', id_encomienda=enc.id_detalle_encomienda))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar la encomienda: {e}', 'danger')

    return render_template('public/encomienda_pago.html', viaje=s.info(), t=t, peso=float(peso),
                           monto=float(monto), metodos=METODOS)


# ---------------------------------------------------------------- comprobante
@encomiendas_bp.route('/comprobante/<int:id_encomienda>')
def comprobante(id_encomienda):
    if id_encomienda not in session.get('encomiendas_emitidas', []):
        flash('Para consultar tu encomienda usa el DNI del destinatario y la clave de recojo.', 'info')
        return redirect(url_for('encomiendas.seguimiento'))
    enc = db.session.get(DetalleEncomienda, id_encomienda)
    if not enc:
        flash('Encomienda no encontrada.', 'warning')
        return redirect(url_for('public.buscar_viaje'))
    r, c = enc.reserva, enc.reserva.cliente
    datos = {'id_encomienda': enc.id_detalle_encomienda, 'fecha_emision': r.fecha_emision,
             'metodo_pago': r.metodo_pago, 'remitente': c.nombres_razon_social if c else '',
             'dni_remitente': c.num_documento if c else '', 'dni_destinatario': enc.dni_destinatario,
             'nombre_destinatario': enc.nombre_destinatario, 'telefono_destinatario': enc.telefono_destinatario,
             'descripcion': enc.descripcion_contenido, 'peso_kg': float(enc.peso_kg),
             'clave_recojo': enc.clave_recojo, 'monto': float(enc.precio_pagado)}
    v = Salida(enc.viaje.horario, enc.viaje.fecha_salida, enc.viaje).info()
    v['fecha_salida'], v['hora_salida'] = v['fecha'], v['hora']
    return render_template('public/encomienda_comprobante.html', e=datos, viaje=v)


# ---------------------------------------------------------------- seguimiento
def _seguimiento(enc):
    v = enc.viaje
    r = v.horario.ruta
    o, d = r.origen, r.destino
    if enc.estado_entrega == 'Entregado':
        etapa = 4
    elif v.estado_viaje == 'Finalizado':
        etapa = 3
    elif v.estado_viaje == 'En Ruta' or enc.estado_entrega == 'En transito':
        etapa = 2
    else:
        etapa = 1
    total = (v.llegada_programada - v.salida_programada).total_seconds()
    prog = 1.0 if etapa >= 3 else 0.0
    if etapa == 2 and total > 0:
        salida = v.salida_real or v.salida_programada
        prog = min(1.0, max(0.0, (datetime.now() - salida).total_seconds() / total))
    coords = lambda s: [float(s.latitud), float(s.longitud), s.nombre_sede] if s.latitud is not None else None
    return {
        'etapa': etapa, 'perdido': enc.estado_entrega == 'Perdido', 'cancelado': v.estado_viaje == 'Cancelado',
        'origen': o.ciudad, 'destino': d.ciudad, 'terminal_destino': d.nombre_sede,
        'salida': v.salida_programada, 'llegada': v.llegada_programada,
        'destinatario': enc.nombre_destinatario, 'peso': float(enc.peso_kg), 'contenido': enc.descripcion_contenido,
        'entregado_en': enc.entregado_en, 'progreso': round(prog * 100),
        'mapa': {'o': coords(o), 'd': coords(d), 'p': prog, 'etapa': etapa},
    }


@encomiendas_bp.route('/seguimiento')
def seguimiento():
    dni = request.args.get('dni', '').strip()
    clave = request.args.get('clave', '').strip().upper()
    envios = None
    if dni or clave:
        encs = DetalleEncomienda.query.filter_by(dni_destinatario=dni, clave_recojo=clave).all() \
            if dni and clave else []
        if encs:
            envios = [_seguimiento(e) for e in encs]
        else:
            flash('No encontramos una encomienda con esos datos. Verifica el DNI y la clave.', 'warning')
    return render_template('public/encomienda_seguimiento.html', envios=envios, dni=dni, clave=clave,
                           etapas=ETAPAS)