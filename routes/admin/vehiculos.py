# routes/admin/vehiculos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Vehiculo

vehiculos_bp = Blueprint(
    'vehiculos',
    __name__,
    url_prefix='/admin/vehiculos'
)


# ============================================================
# 1. LISTAR VEHÍCULOS
# ============================================================
@vehiculos_bp.route('/')
def index():
    vehiculos = Vehiculo.query.all()
    return render_template(
        'admin/vehiculos/index.html',
        vehiculos=vehiculos
    )


# ============================================================
# 2. CREAR VEHÍCULO
# ============================================================
@vehiculos_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        placa = request.form['placa'].strip().upper()
        marca = request.form['marca'].strip()
        modelo = request.form['modelo'].strip()
        color = request.form.get('color', '').strip() or None
        tipo = request.form.get('tipo', 'bus').strip()
        anio_str = request.form.get('anio', '').strip()
        anio = int(anio_str) if anio_str else None
        
        capacidad_asientos = int(request.form['capacidad_asientos'])
        capacidad_carga_kg = float(request.form['capacidad_carga_kg'])
        kilometraje_actual = int(request.form.get('kilometraje_actual', 0))
        estado = request.form.get('estado', 'Disponible')

        try:
            nuevo_vehiculo = Vehiculo(
                placa=placa,
                marca=marca,
                modelo=modelo,
                anio=anio,
                color=color,
                tipo=tipo,
                capacidad_asientos=capacidad_asientos,
                capacidad_carga_kg=capacidad_carga_kg,
                kilometraje_actual=kilometraje_actual,
                estado=estado
            )
            db.session.add(nuevo_vehiculo)
            db.session.commit()

            flash('Vehículo registrado correctamente.', 'success')
            return redirect(url_for('vehiculos.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar vehículo (verifica la placa): {e}', 'danger')

    return render_template('admin/vehiculos/formulario.html')


# ============================================================
# 3. EDITAR VEHÍCULO
# ============================================================
@vehiculos_bp.route('/editar/<int:id_vehiculo>', methods=['GET', 'POST'])
def editar(id_vehiculo):
    vehiculo = db.session.get(Vehiculo, id_vehiculo)

    if not vehiculo:
        flash('Vehículo no encontrado.', 'warning')
        return redirect(url_for('vehiculos.index'))

    if request.method == 'POST':
        try:
            vehiculo.placa = request.form['placa'].strip().upper()
            vehiculo.marca = request.form['marca'].strip()
            vehiculo.modelo = request.form['modelo'].strip()
            vehiculo.color = request.form.get('color', '').strip() or None
            vehiculo.tipo = request.form.get('tipo', vehiculo.tipo).strip()
            
            anio_str = request.form.get('anio', '').strip()
            vehiculo.anio = int(anio_str) if anio_str else None

            vehiculo.capacidad_asientos = int(request.form['capacidad_asientos'])
            vehiculo.capacidad_carga_kg = float(request.form['capacidad_carga_kg'])
            vehiculo.kilometraje_actual = int(request.form.get('kilometraje_actual', vehiculo.kilometraje_actual or 0))
            vehiculo.estado = request.form.get('estado', vehiculo.estado)

            db.session.commit()
            flash('Vehículo actualizado con éxito.', 'success')
            return redirect(url_for('vehiculos.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar vehículo: {e}', 'danger')

    return render_template(
        'admin/vehiculos/formulario.html',
        vehiculo=vehiculo
    )


# ============================================================
# 4. DAR DE BAJA VEHÍCULO
# ============================================================
@vehiculos_bp.route('/eliminar/<int:id_vehiculo>', methods=['POST'])
def eliminar(id_vehiculo):
    vehiculo = db.session.get(Vehiculo, id_vehiculo)
    if vehiculo:
        try:
            vehiculo.estado = 'Baja'
            db.session.commit()
            flash('Vehículo dado de baja correctamente.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al dar de baja el vehículo: {e}', 'danger')
    else:
        flash('Vehículo no encontrado.', 'warning')

    return redirect(url_for('vehiculos.index'))


# ============================================================
# 5. HABILITAR / ACTIVAR VEHÍCULO
# ============================================================
@vehiculos_bp.route('/activar/<int:id_vehiculo>', methods=['POST'])
def activar(id_vehiculo):
    vehiculo = db.session.get(Vehiculo, id_vehiculo)
    if vehiculo:
        try:
            vehiculo.estado = 'Disponible'
            db.session.commit()
            flash('Vehículo habilitado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al habilitar vehículo: {e}', 'danger')
    else:
        flash('Vehículo no encontrado.', 'warning')

    return redirect(url_for('vehiculos.index'))