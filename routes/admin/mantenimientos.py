# routes/admin/mantenimientos.py
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from models import db, Mantenimiento, Vehiculo

mantenimientos_bp = Blueprint('mantenimientos', __name__, url_prefix='/admin/mantenimientos')

TIPOS = ('preventivo', 'correctivo')


def _leer_formulario(form):
    """Valida y convierte los datos del formulario. Retorna (datos, errores)."""
    errores = []
    datos = {}

    try:
        datos['id_vehiculo'] = int(form.get('id_vehiculo', ''))
    except ValueError:
        errores.append('Seleccione un vehículo.')

    tipo = form.get('tipo', '').strip()
    if tipo not in TIPOS:
        errores.append('Seleccione un tipo de mantenimiento válido.')
    datos['tipo'] = tipo

    datos['descripcion'] = form.get('descripcion', '').strip()[:200] or None

    try:
        datos['fecha'] = datetime.strptime(form.get('fecha', ''), '%Y-%m-%d').date()
        if datos['fecha'] > date.today():
            errores.append('La fecha del mantenimiento no puede ser futura.')
    except ValueError:
        errores.append('Ingrese una fecha válida.')

    try:
        datos['km_al_momento'] = int(form.get('km_al_momento', ''))
        if datos['km_al_momento'] < 0:
            errores.append('El kilometraje no puede ser negativo.')
    except ValueError:
        errores.append('Ingrese un kilometraje válido.')

    try:
        datos['costo'] = Decimal(form.get('costo', '0').strip().replace(',', '.') or '0')
        if datos['costo'] < 0:
            errores.append('El costo no puede ser negativo.')
    except InvalidOperation:
        errores.append('Ingrese un costo válido.')

    try:
        datos['dias_inoperativo'] = int(form.get('dias_inoperativo', '0') or 0)
        if datos['dias_inoperativo'] < 0:
            errores.append('Los días inoperativo no pueden ser negativos.')
    except ValueError:
        errores.append('Ingrese un número válido de días inoperativo.')

    return datos, errores


# ============================================================
# 1. LISTAR (con filtros y totales)
# ============================================================
@mantenimientos_bp.route('/')
def index():
    id_vehiculo = request.args.get('id_vehiculo', type=int)
    tipo = request.args.get('tipo', '').strip()

    query = Mantenimiento.query
    if id_vehiculo:
        query = query.filter(Mantenimiento.id_vehiculo == id_vehiculo)
    if tipo in TIPOS:
        query = query.filter(Mantenimiento.tipo == tipo)

    mantenimientos = query.order_by(Mantenimiento.fecha.desc(), Mantenimiento.id_mantenimiento.desc()).limit(300).all()

    # Totales de lo que se está mostrando
    totales = query.with_entities(
        func.count(Mantenimiento.id_mantenimiento),
        func.coalesce(func.sum(Mantenimiento.costo), 0),
        func.coalesce(func.sum(Mantenimiento.dias_inoperativo), 0)
    ).one()

    vehiculos = Vehiculo.query.order_by(Vehiculo.placa).all()

    return render_template(
        'admin/mantenimientos/index.html',
        mantenimientos=mantenimientos, vehiculos=vehiculos, tipos=TIPOS,
        id_vehiculo_sel=id_vehiculo, tipo_sel=tipo,
        total_registros=totales[0], total_costo=float(totales[1]), total_dias=int(totales[2])
    )


# ============================================================
# 2. REGISTRAR
# ============================================================
@mantenimientos_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo():
    vehiculos = Vehiculo.query.filter(Vehiculo.estado != 'Baja').order_by(Vehiculo.placa).all()

    if request.method == 'POST':
        datos, errores = _leer_formulario(request.form)
        if errores:
            for e in errores:
                flash(e, 'warning')
            return render_template('admin/mantenimientos/formulario.html',
                                   mantenimiento=None, vehiculos=vehiculos, tipos=TIPOS,
                                   form=request.form, hoy=date.today().isoformat())
        try:
            mant = Mantenimiento(**datos)
            db.session.add(mant)

            # Mantener sincronizado el kilometraje actual del vehículo
            vehiculo = db.session.get(Vehiculo, datos['id_vehiculo'])
            if vehiculo and datos['km_al_momento'] > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = datos['km_al_momento']

            db.session.commit()
            flash('Mantenimiento registrado correctamente.', 'success')
            return redirect(url_for('mantenimientos.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el mantenimiento: {e}', 'danger')

    return render_template('admin/mantenimientos/formulario.html',
                           mantenimiento=None, vehiculos=vehiculos, tipos=TIPOS,
                           form={}, hoy=date.today().isoformat())


# ============================================================
# 3. EDITAR
# ============================================================
@mantenimientos_bp.route('/editar/<int:id_mantenimiento>', methods=['GET', 'POST'])
def editar(id_mantenimiento):
    mant = db.session.get(Mantenimiento, id_mantenimiento)
    if not mant:
        flash('Mantenimiento no encontrado.', 'warning')
        return redirect(url_for('mantenimientos.index'))

    vehiculos = Vehiculo.query.order_by(Vehiculo.placa).all()

    if request.method == 'POST':
        datos, errores = _leer_formulario(request.form)
        if errores:
            for e in errores:
                flash(e, 'warning')
            return render_template('admin/mantenimientos/formulario.html',
                                   mantenimiento=mant, vehiculos=vehiculos, tipos=TIPOS,
                                   form=request.form, hoy=date.today().isoformat())
        try:
            for campo, valor in datos.items():
                setattr(mant, campo, valor)

            vehiculo = db.session.get(Vehiculo, datos['id_vehiculo'])
            if vehiculo and datos['km_al_momento'] > vehiculo.kilometraje_actual:
                vehiculo.kilometraje_actual = datos['km_al_momento']

            db.session.commit()
            flash('Mantenimiento actualizado con éxito.', 'success')
            return redirect(url_for('mantenimientos.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el mantenimiento: {e}', 'danger')

    return render_template('admin/mantenimientos/formulario.html',
                           mantenimiento=mant, vehiculos=vehiculos, tipos=TIPOS,
                           form={}, hoy=date.today().isoformat())