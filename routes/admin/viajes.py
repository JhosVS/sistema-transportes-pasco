# routes/admin/viajes.py
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Horario, Ruta, Vehiculo, Conductor

admin_viajes_bp = Blueprint('admin_viajes', __name__, url_prefix='/admin/horarios')


# ============================================================
# 1. LISTAR HORARIOS
# ============================================================
@admin_viajes_bp.route('/')
def index():
    horarios = Horario.query.all()
    return render_template('admin/viajes/index.html', horarios=horarios)


# ============================================================
# 2. CREAR HORARIO
# ============================================================
@admin_viajes_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        id_ruta = int(request.form['id_ruta'])
        id_vehiculo_default_str = request.form.get('id_vehiculo_default', '').strip()
        id_conductor_default_str = request.form.get('id_conductor_default', '').strip()
        dia_semana = request.form['dia_semana'].strip()
        hora_salida_str = request.form['hora_salida'].strip()
        precio_pasaje_base = float(request.form['precio_pasaje_base'])
        precio_kg_carga_base = float(request.form['precio_kg_carga_base'])
        estado = request.form.get('estado', 'Activo')

        try:
            try:
                hora_salida = datetime.strptime(hora_salida_str, '%H:%M').time()
            except ValueError:
                hora_salida = datetime.strptime(hora_salida_str, '%H:%M:%S').time()

            nuevo_horario = Horario(
                id_ruta=id_ruta,
                id_vehiculo_default=int(id_vehiculo_default_str) if id_vehiculo_default_str else None,
                id_conductor_default=int(id_conductor_default_str) if id_conductor_default_str else None,
                dia_semana=dia_semana,
                hora_salida=hora_salida,
                precio_pasaje_base=precio_pasaje_base,
                precio_kg_carga_base=precio_kg_carga_base,
                estado=estado
            )
            db.session.add(nuevo_horario)
            db.session.commit()

            flash('Horario recurrente registrado correctamente.', 'success')
            return redirect(url_for('admin_viajes.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el horario (verifique duplicados de ruta, día y hora): {e}', 'danger')

    rutas = Ruta.query.filter_by(activa=True).all()
    vehiculos = Vehiculo.query.filter(Vehiculo.estado != 'Baja').all()
    conductores = Conductor.query.filter_by(estado='Activo').all()

    return render_template(
        'admin/viajes/formulario.html',
        horario=None,
        rutas=rutas,
        vehiculos=vehiculos,
        conductores=conductores
    )


# ============================================================
# 3. EDITAR HORARIO
# ============================================================
@admin_viajes_bp.route('/editar/<int:id_horario>', methods=['GET', 'POST'])
def editar(id_horario):
    horario = db.session.get(Horario, id_horario)
    if not horario:
        flash('Horario no encontrado.', 'warning')
        return redirect(url_for('admin_viajes.index'))

    if request.method == 'POST':
        try:
            horario.id_ruta = int(request.form['id_ruta'])
            
            id_vehiculo_default_str = request.form.get('id_vehiculo_default', '').strip()
            id_conductor_default_str = request.form.get('id_conductor_default', '').strip()
            
            horario.id_vehiculo_default = int(id_vehiculo_default_str) if id_vehiculo_default_str else None
            horario.id_conductor_default = int(id_conductor_default_str) if id_conductor_default_str else None
            horario.dia_semana = request.form['dia_semana'].strip()
            
            hora_salida_str = request.form['hora_salida'].strip()
            try:
                horario.hora_salida = datetime.strptime(hora_salida_str, '%H:%M').time()
            except ValueError:
                horario.hora_salida = datetime.strptime(hora_salida_str, '%H:%M:%S').time()

            horario.precio_pasaje_base = float(request.form['precio_pasaje_base'])
            horario.precio_kg_carga_base = float(request.form['precio_kg_carga_base'])
            horario.estado = request.form.get('estado', horario.estado)

            db.session.commit()
            flash('Horario actualizado con éxito.', 'success')
            return redirect(url_for('admin_viajes.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar horario: {e}', 'danger')

    rutas = Ruta.query.filter_by(activa=True).all()
    vehiculos = Vehiculo.query.filter(Vehiculo.estado != 'Baja').all()
    conductores = Conductor.query.filter_by(estado='Activo').all()

    return render_template(
        'admin/viajes/formulario.html',
        horario=horario,
        rutas=rutas,
        vehiculos=vehiculos,
        conductores=conductores
    )


# ============================================================
# 4. DESACTIVAR HORARIO
# ============================================================
@admin_viajes_bp.route('/eliminar/<int:id_horario>', methods=['POST'])
def eliminar(id_horario):
    horario = db.session.get(Horario, id_horario)
    if horario:
        try:
            horario.estado = 'Inactivo'
            db.session.commit()
            flash('Horario desactivado correctamente.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al desactivar horario: {e}', 'danger')
    else:
        flash('Horario no encontrado.', 'warning')

    return redirect(url_for('admin_viajes.index'))


# ============================================================
# 5. ACTIVAR HORARIO
# ============================================================
@admin_viajes_bp.route('/activar/<int:id_horario>', methods=['POST'])
def activar(id_horario):
    horario = db.session.get(Horario, id_horario)
    if horario:
        try:
            horario.estado = 'Activo'
            db.session.commit()
            flash('Horario activado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al activar horario: {e}', 'danger')
    else:
        flash('Horario no encontrado.', 'warning')

    return redirect(url_for('admin_viajes.index'))