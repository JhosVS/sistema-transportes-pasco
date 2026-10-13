# app/routes/admin/conductores.py
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Conductor

conductores_bp = Blueprint(
    'conductores',
    __name__,
    url_prefix='/admin/conductores'
)


# ============================================================
# 1. LISTAR CONDUCTORES
# ============================================================
@conductores_bp.route('/')
def index():
    conductores = Conductor.query.all()
    return render_template(
        'admin/conductores/index.html',
        conductores=conductores,
        hoy=date.today()
    )


# ============================================================
# 2. CREAR CONDUCTOR
# ============================================================
@conductores_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        dni = request.form['dni'].strip()
        nombres = request.form['nombres'].strip()
        apellidos = request.form['apellidos'].strip()
        telefono = request.form['telefono'].strip()
        licencia_conducir = request.form['licencia_conducir'].strip().upper()
        licencia_categoria = request.form.get('licencia_categoria', 'A-IIIc').strip()
        
        licencia_vence_str = request.form.get('licencia_vence', '').strip()
        fecha_ingreso_str = request.form.get('fecha_ingreso', '').strip()
        estado = request.form.get('estado', 'Activo')

        try:
            licencia_vence = datetime.strptime(licencia_vence_str, '%Y-%m-%d').date() if licencia_vence_str else date.today()
            fecha_ingreso = datetime.strptime(fecha_ingreso_str, '%Y-%m-%d').date() if fecha_ingreso_str else None

            nuevo_conductor = Conductor(
                dni=dni,
                nombres=nombres,
                apellidos=apellidos,
                telefono=telefono,
                licencia_conducir=licencia_conducir,
                licencia_categoria=licencia_categoria,
                licencia_vence=licencia_vence,
                fecha_ingreso=fecha_ingreso,
                estado=estado
            )
            db.session.add(nuevo_conductor)
            db.session.commit()

            flash('Conductor registrado correctamente.', 'success')
            return redirect(url_for('conductores.index'))

        except ValueError:
            flash('Error en el formato de las fechas proporcionadas.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar conductor (verifica DNI o licencia): {e}', 'danger')

    return render_template('admin/conductores/formulario.html')


# ============================================================
# 3. EDITAR CONDUCTOR
# ============================================================
@conductores_bp.route('/editar/<int:id_conductor>', methods=['GET', 'POST'])
def editar(id_conductor):
    conductor = db.session.get(Conductor, id_conductor)

    if not conductor:
        flash('Conductor no encontrado.', 'warning')
        return redirect(url_for('conductores.index'))

    if request.method == 'POST':
        try:
            conductor.dni = request.form['dni'].strip()
            conductor.nombres = request.form['nombres'].strip()
            conductor.apellidos = request.form['apellidos'].strip()
            conductor.telefono = request.form['telefono'].strip()
            conductor.licencia_conducir = request.form['licencia_conducir'].strip().upper()
            conductor.licencia_categoria = request.form.get('licencia_categoria', conductor.licencia_categoria).strip()
            
            licencia_vence_str = request.form.get('licencia_vence', '').strip()
            if licencia_vence_str:
                conductor.licencia_vence = datetime.strptime(licencia_vence_str, '%Y-%m-%d').date()

            fecha_ingreso_str = request.form.get('fecha_ingreso', '').strip()
            conductor.fecha_ingreso = datetime.strptime(fecha_ingreso_str, '%Y-%m-%d').date() if fecha_ingreso_str else None

            conductor.estado = request.form.get('estado', conductor.estado)

            db.session.commit()
            flash('Conductor actualizado con éxito.', 'success')
            return redirect(url_for('conductores.index'))

        except ValueError:
            flash('Error en el formato de las fechas proporcionadas.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar conductor: {e}', 'danger')

    return render_template(
        'admin/conductores/formulario.html',
        conductor=conductor
    )


# ============================================================
# 4. DESACTIVAR CONDUCTOR
# ============================================================
@conductores_bp.route('/eliminar/<int:id_conductor>', methods=['POST'])
def eliminar(id_conductor):
    conductor = db.session.get(Conductor, id_conductor)
    if conductor:
        try:
            conductor.estado = 'Inactivo'
            db.session.commit()
            flash('Conductor desactivado correctamente.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al desactivar conductor: {e}', 'danger')
    else:
        flash('Conductor no encontrado.', 'warning')

    return redirect(url_for('conductores.index'))


# ============================================================
# 5. ACTIVAR CONDUCTOR
# ============================================================
@conductores_bp.route('/activar/<int:id_conductor>', methods=['POST'])
def activar(id_conductor):
    conductor = db.session.get(Conductor, id_conductor)
    if conductor:
        try:
            conductor.estado = 'Activo'
            db.session.commit()
            flash('Conductor activado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al activar conductor: {e}', 'danger')
    else:
        flash('Conductor no encontrado.', 'warning')

    return redirect(url_for('conductores.index'))