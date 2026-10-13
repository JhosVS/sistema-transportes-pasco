# routes/admin/combustible.py
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from models import db, Combustible, Vehiculo, ProgramacionViaje

combustible_bp = Blueprint('combustible', __name__, url_prefix='/admin/combustible')

MAX_GALONES = Decimal('300')   # límite razonable por carga de un bus
FORMATO_FECHA = '%Y-%m-%dT%H:%M'


def _leer_formulario(form, id_carga_actual=None):
    """Valida y convierte los datos del formulario. Retorna (datos, errores)."""
    errores = []
    datos = {}

    try:
        datos['id_vehiculo'] = int(form.get('id_vehiculo', ''))
    except ValueError:
        errores.append('Seleccione un vehículo.')

    viaje_str = form.get('id_viaje', '').strip()
    datos['id_viaje'] = int(viaje_str) if viaje_str.isdigit() else None

    try:
        datos['fecha'] = datetime.strptime(form.get('fecha', ''), FORMATO_FECHA)
        if datos['fecha'] > datetime.now():
            errores.append('La fecha de la carga no puede ser futura.')
    except ValueError:
        errores.append('Ingrese una fecha y hora válidas.')

    try:
        datos['galones'] = Decimal(form.get('galones', '').strip().replace(',', '.'))
        if datos['galones'] <= 0 or datos['galones'] > MAX_GALONES:
            errores.append(f'Los galones deben estar entre 0.01 y {MAX_GALONES}.')
    except InvalidOperation:
        errores.append('Ingrese una cantidad válida de galones.')

    try:
        datos['costo_total'] = Decimal(form.get('costo_total', '').strip().replace(',', '.'))
        if datos['costo_total'] <= 0:
            errores.append('El costo total debe ser mayor a cero.')
    except InvalidOperation:
        errores.append('Ingrese un costo total válido.')

    try:
        datos['km_odometro'] = int(form.get('km_odometro', ''))
        if datos['km_odometro'] < 0:
            errores.append('El odómetro no puede ser negativo.')
    except ValueError:
        errores.append('Ingrese un odómetro válido.')

    # --- Validaciones cruzadas (solo si lo básico está bien) ---
    if not errores:
        # El viaje debe corresponder al vehículo
        if datos['id_viaje']:
            viaje = db.session.get(ProgramacionViaje, datos['id_viaje'])
            veh_viaje = viaje.vehiculo_efectivo if viaje else None
            if not viaje:
                errores.append('El viaje seleccionado no existe.')
            elif not veh_viaje or veh_viaje.id_vehiculo != datos['id_vehiculo']:
                errores.append('El viaje seleccionado no corresponde a ese vehículo.')

        # El odómetro debe ser coherente con las cargas vecinas del mismo vehículo
        base = Combustible.query.filter(Combustible.id_vehiculo == datos['id_vehiculo'])
        if id_carga_actual:
            base = base.filter(Combustible.id_carga != id_carga_actual)

        anterior = base.filter(Combustible.fecha <= datos['fecha']) \
                       .order_by(Combustible.fecha.desc(), Combustible.id_carga.desc()).first()
        posterior = base.filter(Combustible.fecha > datos['fecha']) \
                        .order_by(Combustible.fecha.asc(), Combustible.id_carga.asc()).first()

        if anterior and datos['km_odometro'] < anterior.km_odometro:
            errores.append(
                f'El odómetro ({datos["km_odometro"]:,} km) es menor al de la carga anterior '
                f'({anterior.km_odometro:,} km del {anterior.fecha.strftime("%d/%m/%Y %H:%M")}).')
        if posterior and datos['km_odometro'] > posterior.km_odometro:
            errores.append(
                f'El odómetro ({datos["km_odometro"]:,} km) es mayor al de una carga posterior '
                f'({posterior.km_odometro:,} km del {posterior.fecha.strftime("%d/%m/%Y %H:%M")}).')

    return datos, errores


def _viajes_para_selector(carga=None):
    """Últimos 30 viajes (más el viaje actual de la carga, si se está editando)."""
    viajes = ProgramacionViaje.query.order_by(ProgramacionViaje.fecha_salida.desc()).limit(30).all()
    if carga and carga.viaje and carga.viaje not in viajes:
        viajes.append(carga.viaje)
    return viajes


def _render_formulario(carga, form):
    vehiculos = Vehiculo.query.order_by(Vehiculo.placa).all() if carga else \
        Vehiculo.query.filter(Vehiculo.estado != 'Baja').order_by(Vehiculo.placa).all()
    return render_template(
        'admin/combustible/formulario.html',
        carga=carga, vehiculos=vehiculos, viajes=_viajes_para_selector(carga),
        form=form, ahora=datetime.now().strftime(FORMATO_FECHA)
    )


# ============================================================
# 1. LISTAR (con filtros, totales y rendimiento km/galón)
# ============================================================
@combustible_bp.route('/')
def index():
    id_vehiculo = request.args.get('id_vehiculo', type=int)
    desde_str = request.args.get('desde', '').strip()
    hasta_str = request.args.get('hasta', '').strip()

    query = Combustible.query
    if id_vehiculo:
        query = query.filter(Combustible.id_vehiculo == id_vehiculo)
    try:
        if desde_str:
            query = query.filter(Combustible.fecha >= datetime.strptime(desde_str, '%Y-%m-%d'))
        if hasta_str:
            fin = datetime.strptime(hasta_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Combustible.fecha <= fin)
    except ValueError:
        flash('Fecha de filtro inválida.', 'warning')

    cargas = query.order_by(Combustible.fecha.desc(), Combustible.id_carga.desc()).limit(300).all()

    # Rendimiento: usa el historial completo del vehículo (no solo lo filtrado)
    rendimiento = {}
    ultimo_km = {}
    historial = db.session.query(
        Combustible.id_carga, Combustible.id_vehiculo, Combustible.km_odometro, Combustible.galones
    ).order_by(Combustible.id_vehiculo, Combustible.fecha, Combustible.id_carga).all()
    for id_carga, id_veh, km, gal in historial:
        previo = ultimo_km.get(id_veh)
        if previo is not None and km > previo and gal and gal > 0:
            rendimiento[id_carga] = round((km - previo) / float(gal), 1)
        ultimo_km[id_veh] = km

    totales = query.with_entities(
        func.count(Combustible.id_carga),
        func.coalesce(func.sum(Combustible.galones), 0),
        func.coalesce(func.sum(Combustible.costo_total), 0)
    ).one()
    total_galones, total_costo = float(totales[1]), float(totales[2])
    precio_promedio = (total_costo / total_galones) if total_galones else 0

    vehiculos = Vehiculo.query.order_by(Vehiculo.placa).all()

    return render_template(
        'admin/combustible/index.html',
        cargas=cargas, vehiculos=vehiculos, rendimiento=rendimiento,
        id_vehiculo_sel=id_vehiculo, desde=desde_str, hasta=hasta_str,
        total_registros=totales[0], total_galones=total_galones,
        total_costo=total_costo, precio_promedio=precio_promedio
    )


# ============================================================
# 2. REGISTRAR CARGA
# ============================================================
@combustible_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    if request.method == 'POST':
        datos, errores = _leer_formulario(request.form)
        if errores:
            for e in errores:
                flash(e, 'warning')
            return _render_formulario(None, request.form)
        try:
            db.session.add(Combustible(**datos))

            vehiculo = db.session.get(Vehiculo, datos['id_vehiculo'])
            if vehiculo and datos['km_odometro'] > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = datos['km_odometro']

            db.session.commit()
            flash('Carga de combustible registrada correctamente.', 'success')
            return redirect(url_for('combustible.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar la carga: {e}', 'danger')

    return _render_formulario(None, {})


# ============================================================
# 3. EDITAR CARGA
# ============================================================
@combustible_bp.route('/editar/<int:id_carga>', methods=['GET', 'POST'])
def editar(id_carga):
    carga = db.session.get(Combustible, id_carga)
    if not carga:
        flash('Carga no encontrada.', 'warning')
        return redirect(url_for('combustible.index'))

    if request.method == 'POST':
        datos, errores = _leer_formulario(request.form, id_carga_actual=id_carga)
        if errores:
            for e in errores:
                flash(e, 'warning')
            return _render_formulario(carga, request.form)
        try:
            for campo, valor in datos.items():
                setattr(carga, campo, valor)

            vehiculo = db.session.get(Vehiculo, datos['id_vehiculo'])
            if vehiculo and datos['km_odometro'] > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = datos['km_odometro']

            db.session.commit()
            flash('Carga actualizada con éxito.', 'success')
            return redirect(url_for('combustible.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la carga: {e}', 'danger')

    return _render_formulario(carga, {})