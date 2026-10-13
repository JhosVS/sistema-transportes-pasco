# routes/admin/rutas.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Ruta, Sede

rutas_bp = Blueprint('rutas', __name__, url_prefix='/admin/rutas')


# ============================================================
# 1. LISTAR RUTAS
# ============================================================
@rutas_bp.route('/')
def index():
    rutas = Ruta.query.all()
    return render_template('admin/rutas/index.html', rutas=rutas)


# ============================================================
# 2. CREAR RUTA
# ============================================================
@rutas_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        id_sede_origen = int(request.form['id_sede_origen'])
        id_sede_destino = int(request.form['id_sede_destino'])
        distancia_km = float(request.form['distancia_km'])
        duracion_estimada_hrs = float(request.form['duracion_estimada_hrs'])
        precio_base = float(request.form['precio_base'])
        activa = request.form.get('activa', '1') == '1'

        if id_sede_origen == id_sede_destino:
            flash('La sede de origen y la sede de destino no pueden ser la misma.', 'warning')
        else:
            try:
                nueva_ruta = Ruta(
                    id_sede_origen=id_sede_origen,
                    id_sede_destino=id_sede_destino,
                    distancia_km=distancia_km,
                    duracion_estimada_hrs=duracion_estimada_hrs,
                    precio_base=precio_base,
                    activa=activa
                )
                db.session.add(nueva_ruta)
                db.session.commit()
                flash('Ruta registrada correctamente.', 'success')
                return redirect(url_for('rutas.index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar la ruta (verifique que el trayecto no exista previamente): {e}', 'danger')

    sedes = Sede.query.filter_by(activo=True).all()
    return render_template('admin/rutas/formulario.html', ruta=None, sedes=sedes)


# ============================================================
# 3. EDITAR RUTA
# ============================================================
@rutas_bp.route('/editar/<int:id_ruta>', methods=['GET', 'POST'])
def editar(id_ruta):
    ruta = db.session.get(Ruta, id_ruta)
    if not ruta:
        flash('Ruta no encontrada.', 'warning')
        return redirect(url_for('rutas.index'))

    if request.method == 'POST':
        id_sede_origen = int(request.form['id_sede_origen'])
        id_sede_destino = int(request.form['id_sede_destino'])

        if id_sede_origen == id_sede_destino:
            flash('La sede de origen y la sede de destino no pueden ser la misma.', 'warning')
        else:
            try:
                ruta.id_sede_origen = id_sede_origen
                ruta.id_sede_destino = id_sede_destino
                ruta.distancia_km = float(request.form['distancia_km'])
                ruta.duracion_estimada_hrs = float(request.form['duracion_estimada_hrs'])
                ruta.precio_base = float(request.form['precio_base'])
                ruta.activa = request.form.get('activa', '1') == '1'

                db.session.commit()
                flash('Ruta actualizada con éxito.', 'success')
                return redirect(url_for('rutas.index'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar la ruta: {e}', 'danger')

    sedes = Sede.query.filter_by(activo=True).all()
    return render_template('admin/rutas/formulario.html', ruta=ruta, sedes=sedes)


# ============================================================
# 4. DESACTIVAR RUTA (Baja Lógica)
# ============================================================
@rutas_bp.route('/eliminar/<int:id_ruta>', methods=['POST'])
def eliminar(id_ruta):
    ruta = db.session.get(Ruta, id_ruta)
    if ruta:
        try:
            ruta.activa = False
            db.session.commit()
            flash('Ruta desactivada correctamente.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al desactivar la ruta: {e}', 'danger')
    else:
        flash('Ruta no encontrada.', 'warning')

    return redirect(url_for('rutas.index'))


# ============================================================
# 5. ACTIVAR RUTA
# ============================================================
@rutas_bp.route('/activar/<int:id_ruta>', methods=['POST'])
def activar(id_ruta):
    ruta = db.session.get(Ruta, id_ruta)
    if ruta:
        try:
            ruta.activa = True
            db.session.commit()
            flash('Ruta activada correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al activar la ruta: {e}', 'danger')
    else:
        flash('Ruta no encontrada.', 'warning')

    return redirect(url_for('rutas.index'))