from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import VehiculoModel

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
    vehiculos = VehiculoModel.get_todos()

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
        color = request.form['color'].strip()
        capacidad_asientos = request.form['capacidad_asientos']
        capacidad_carga_kg = request.form['capacidad_carga_kg']
        estado = request.form['estado']

        try:
            VehiculoModel.crear(
                placa,
                marca,
                modelo,
                color,
                capacidad_asientos,
                capacidad_carga_kg,
                estado
            )

            flash(
                'Vehículo registrado correctamente.',
                'success'
            )

            return redirect(url_for('vehiculos.index'))

        except Exception as e:
            flash(
                f'Error al registrar vehículo (Verifica la placa): {e}',
                'danger'
            )

    return render_template(
        'admin/vehiculos/formulario.html'
    )


# ============================================================
# 3. EDITAR VEHÍCULO
# ============================================================
@vehiculos_bp.route('/editar/<int:id_vehiculo>', methods=['GET', 'POST'])
def editar(id_vehiculo):

    vehiculo = VehiculoModel.get_by_id(id_vehiculo)

    if not vehiculo:
        flash(
            'Vehículo no encontrado.',
            'warning'
        )

        return redirect(url_for('vehiculos.index'))

    if request.method == 'POST':

        placa = request.form['placa'].strip().upper()
        marca = request.form['marca'].strip()
        modelo = request.form['modelo'].strip()
        color = request.form['color'].strip()
        capacidad_asientos = request.form['capacidad_asientos']
        capacidad_carga_kg = request.form['capacidad_carga_kg']
        estado = request.form['estado']

        try:
            VehiculoModel.actualizar(
                id_vehiculo,
                placa,
                marca,
                modelo,
                color,
                capacidad_asientos,
                capacidad_carga_kg,
                estado
            )

            flash(
                'Vehículo actualizado con éxito.',
                'success'
            )

            return redirect(url_for('vehiculos.index'))

        except Exception as e:
            flash(
                f'Error al actualizar vehículo: {e}',
                'danger'
            )

    return render_template(
        'admin/vehiculos/formulario.html',
        vehiculo=vehiculo
    )


# ============================================================
# 4. DESACTIVAR VEHÍCULO
# ============================================================
@vehiculos_bp.route('/eliminar/<int:id_vehiculo>', methods=['POST'])
def eliminar(id_vehiculo):

    try:
        VehiculoModel.eliminar(id_vehiculo)

        flash(
            'Vehículo desactivado correctamente.',
            'info'
        )

    except Exception as e:
        flash(
            f'Error al desactivar vehículo: {e}',
            'danger'
        )

    return redirect(url_for('vehiculos.index'))

# 5. ACTIVAR VEHÍCULO
@vehiculos_bp.route('/activar/<int:id_vehiculo>', methods=['POST'])
def activar(id_vehiculo):

    try:
        VehiculoModel.activar(id_vehiculo)

        flash(
            'Vehículo activado correctamente.',
            'success'
        )

    except Exception as e:
        flash(
            f'Error al activar vehículo: {e}',
            'danger'
        )

    return redirect(url_for('vehiculos.index'))