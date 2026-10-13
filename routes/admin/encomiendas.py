# routes/admin/encomiendas.py
import secrets
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from models import db, DetalleEncomienda, ProgramacionViaje

encomiendas_admin_bp = Blueprint('encomiendas_admin', __name__, url_prefix='/admin/encomiendas')

ESTADOS = ('Registrado', 'En transito', 'Entregado', 'Perdido')

# Transiciones permitidas. "Entregado" tiene su propia ruta porque exige validar la clave.
TRANSICIONES = {
    'Registrado': ['En transito', 'Perdido'],
    'En transito': ['Perdido'],
    'Entregado': [],
    'Perdido': [],
}


# ============================================================
# 1. LISTAR CON FILTROS
# ============================================================
@encomiendas_admin_bp.route('/')
def index():
    q = request.args.get('q', '').strip()
    estado = request.args.get('estado', '').strip()
    id_viaje = request.args.get('id_viaje', type=int)

    query = DetalleEncomienda.query

    if estado in ESTADOS:
        query = query.filter(DetalleEncomienda.estado_entrega == estado)
    if id_viaje:
        query = query.filter(DetalleEncomienda.id_viaje == id_viaje)
    if q:
        like = f'%{q}%'
        query = query.filter(db.or_(
            DetalleEncomienda.dni_destinatario.like(like),
            DetalleEncomienda.clave_recojo == q.upper(),
            DetalleEncomienda.nombre_destinatario.like(like),
        ))

    encomiendas = query.order_by(DetalleEncomienda.id_detalle_encomienda.desc()).limit(200).all()

    conteo = dict(
        db.session.query(DetalleEncomienda.estado_entrega, func.count())
        .group_by(DetalleEncomienda.estado_entrega).all()
    )

    viajes = ProgramacionViaje.query.order_by(ProgramacionViaje.fecha_salida.desc()).limit(30).all()

    return render_template(
        'admin/encomiendas/index.html',
        encomiendas=encomiendas, conteo=conteo, viajes=viajes,
        q=q, estado_sel=estado, id_viaje_sel=id_viaje,
        estados=ESTADOS, transiciones=TRANSICIONES
    )


# ============================================================
# 2. DETALLE
# ============================================================
@encomiendas_admin_bp.route('/<int:id_encomienda>')
def detalle(id_encomienda):
    enc = db.session.get(DetalleEncomienda, id_encomienda)
    if not enc:
        flash('Encomienda no encontrada.', 'warning')
        return redirect(url_for('encomiendas_admin.index'))

    return render_template(
        'admin/encomiendas/detalle.html',
        e=enc, transiciones=TRANSICIONES
    )


# ============================================================
# 3. CAMBIAR ESTADO (Registrado -> En transito, o Perdido)
# ============================================================
@encomiendas_admin_bp.route('/estado/<int:id_encomienda>', methods=['POST'])
def cambiar_estado(id_encomienda):
    enc = db.session.get(DetalleEncomienda, id_encomienda)
    destino = request.form.get('nuevo_estado', '').strip()
    volver = request.form.get('volver', 'index')

    if not enc:
        flash('Encomienda no encontrada.', 'warning')
        return redirect(url_for('encomiendas_admin.index'))

    if destino not in TRANSICIONES.get(enc.estado_entrega, []):
        flash(f'No se puede pasar de "{enc.estado_entrega}" a "{destino}".', 'warning')
    else:
        try:
            enc.estado_entrega = destino
            db.session.commit()
            flash(f'Encomienda E001-{enc.id_detalle_encomienda:06d} marcada como "{destino}".', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al cambiar el estado: {e}', 'danger')

    if volver == 'detalle':
        return redirect(url_for('encomiendas_admin.detalle', id_encomienda=id_encomienda))
    return redirect(url_for('encomiendas_admin.index', **request.args))


# ============================================================
# 4. REGISTRAR ENTREGA (valida DNI + clave de recojo)
# ============================================================
@encomiendas_admin_bp.route('/entregar/<int:id_encomienda>', methods=['POST'])
def entregar(id_encomienda):
    enc = db.session.get(DetalleEncomienda, id_encomienda)
    if not enc:
        flash('Encomienda no encontrada.', 'warning')
        return redirect(url_for('encomiendas_admin.index'))

    if enc.estado_entrega != 'En transito':
        flash('Solo se puede entregar una encomienda que esté "En transito".', 'warning')
        return redirect(url_for('encomiendas_admin.detalle', id_encomienda=id_encomienda))

    dni = request.form.get('dni_destinatario', '').strip()
    clave = request.form.get('clave_recojo', '').strip().upper()

    dni_ok = secrets.compare_digest(dni, enc.dni_destinatario)
    clave_ok = secrets.compare_digest(clave, enc.clave_recojo.upper())

    if not (dni_ok and clave_ok):
        flash('El DNI o la clave de recojo no coinciden. No se registró la entrega.', 'danger')
        return redirect(url_for('encomiendas_admin.detalle', id_encomienda=id_encomienda))

    try:
        enc.estado_entrega = 'Entregado'
        enc.entregado_en = datetime.now()
        db.session.commit()
        flash('Entrega registrada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar la entrega: {e}', 'danger')

    return redirect(url_for('encomiendas_admin.detalle', id_encomienda=id_encomienda))