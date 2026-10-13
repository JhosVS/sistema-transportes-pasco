# routes/admin/sedes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Sede

sedes_bp = Blueprint('sedes', __name__, url_prefix='/admin/sedes')


# ============================================================
# 1. LISTAR SEDES
# ============================================================
@sedes_bp.route('/')
def index():
    sedes = Sede.query.all()
    return render_template('admin/sedes/index.html', sedes=sedes)


# ============================================================
# 2. CREAR SEDE
# ============================================================
@sedes_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        nombre_sede = request.form['nombre_sede'].strip()
        ciudad = request.form['ciudad'].strip()
        departamento = request.form['departamento'].strip()
        direccion = request.form['direccion'].strip()
        
        altitud_str = request.form.get('altitud_msnm', '').strip()
        latitud_str = request.form.get('latitud', '').strip()
        longitud_str = request.form.get('longitud', '').strip()
        activo = request.form.get('activo', '1') == '1'

        try:
            nueva_sede = Sede(
                nombre_sede=nombre_sede,
                ciudad=ciudad,
                departamento=departamento,
                direccion=direccion,
                altitud_msnm=int(altitud_str) if altitud_str else None,
                latitud=float(latitud_str) if latitud_str else None,
                longitud=float(longitud_str) if longitud_str else None,
                activo=activo
            )
            db.session.add(nueva_sede)
            db.session.commit()
            flash('Sede registrada correctamente.', 'success')
            return redirect(url_for('sedes.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar sede: {e}', 'danger')

    return render_template('admin/sedes/formulario.html', sede=None)


# ============================================================
# 3. EDITAR SEDE
# ============================================================
@sedes_bp.route('/editar/<int:id_sede>', methods=['GET', 'POST'])
def editar(id_sede):
    sede = db.session.get(Sede, id_sede)
    if not sede:
        flash('Sede no encontrada.', 'warning')
        return redirect(url_for('sedes.index'))

    if request.method == 'POST':
        try:
            sede.nombre_sede = request.form['nombre_sede'].strip()
            sede.ciudad = request.form['ciudad'].strip()
            sede.departamento = request.form['departamento'].strip()
            sede.direccion = request.form['direccion'].strip()

            altitud_str = request.form.get('altitud_msnm', '').strip()
            latitud_str = request.form.get('latitud', '').strip()
            longitud_str = request.form.get('longitud', '').strip()

            sede.altitud_msnm = int(altitud_str) if altitud_str else None
            sede.latitud = float(latitud_str) if latitud_str else None
            sede.longitud = float(longitud_str) if longitud_str else None
            sede.activo = request.form.get('activo', '1') == '1'

            db.session.commit()
            flash('Sede actualizada con éxito.', 'success')
            return redirect(url_for('sedes.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar sede: {e}', 'danger')

    return render_template('admin/sedes/formulario.html', sede=sede)


# ============================================================
# 4. DESACTIVAR SEDE (Baja Lógica)
# ============================================================
@sedes_bp.route('/eliminar/<int:id_sede>', methods=['POST'])
def eliminar(id_sede):
    sede = db.session.get(Sede, id_sede)
    if sede:
        try:
            sede.activo = False
            db.session.commit()
            flash('Sede desactivada correctamente.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al desactivar la sede: {e}', 'danger')
    else:
        flash('Sede no encontrada.', 'warning')

    return redirect(url_for('sedes.index'))


# ============================================================
# 5. ACTIVAR SEDE
# ============================================================
@sedes_bp.route('/activar/<int:id_sede>', methods=['POST'])
def activar(id_sede):
    sede = db.session.get(Sede, id_sede)
    if sede:
        try:
            sede.activo = True
            db.session.commit()
            flash('Sede activada correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al activar la sede: {e}', 'danger')
    else:
        flash('Sede no encontrada.', 'warning')

    return redirect(url_for('sedes.index'))