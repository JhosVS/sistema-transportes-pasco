from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import ConductorModel

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
    conductores = ConductorModel.get_todos()

    return render_template(
        'admin/conductores/index.html',
        conductores=conductores
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
        estado = request.form['estado']

        try:
            ConductorModel.crear(
                dni,
                nombres,
                apellidos,
                telefono,
                licencia_conducir,
                estado
            )

            flash(
                'Conductor registrado correctamente.',
                'success'
            )

            return redirect(url_for('conductores.index'))

        except Exception as e:
            flash(
                f'Error al registrar conductor (verifica DNI o licencia): {e}',
                'danger'
            )

    return render_template(
        'admin/conductores/formulario.html'
    )


# ============================================================
# 3. EDITAR CONDUCTOR
# ============================================================
@conductores_bp.route('/editar/<int:id_conductor>', methods=['GET', 'POST'])
def editar(id_conductor):

    conductor = ConductorModel.get_by_id(id_conductor)

    if not conductor:
        flash(
            'Conductor no encontrado.',
            'warning'
        )

        return redirect(url_for('conductores.index'))

    if request.method == 'POST':

        dni = request.form['dni'].strip()
        nombres = request.form['nombres'].strip()
        apellidos = request.form['apellidos'].strip()
        telefono = request.form['telefono'].strip()
        licencia_conducir = request.form['licencia_conducir'].strip().upper()
        estado = request.form['estado']

        try:
            ConductorModel.actualizar(
                id_conductor,
                dni,
                nombres,
                apellidos,
                telefono,
                licencia_conducir,
                estado
            )

            flash(
                'Conductor actualizado con éxito.',
                'success'
            )

            return redirect(url_for('conductores.index'))

        except Exception as e:
            flash(
                f'Error al actualizar conductor: {e}',
                'danger'
            )

    return render_template(
        'admin/conductores/formulario.html',
        conductor=conductor
    )


# ============================================================
# 4. DESACTIVAR CONDUCTOR
# ============================================================
@conductores_bp.route('/eliminar/<int:id_conductor>', methods=['POST'])
def eliminar(id_conductor):

    try:
        ConductorModel.eliminar(id_conductor)

        flash(
            'Conductor desactivado correctamente.',
            'info'
        )

    except Exception as e:
        flash(
            f'Error al desactivar conductor: {e}',
            'danger'
        )

    return redirect(url_for('conductores.index'))

# ============================================================
# 5. ACTIVAR CONDUCTOR
# ============================================================
@conductores_bp.route('/activar/<int:id_conductor>', methods=['POST'])
def activar(id_conductor):

    try:
        ConductorModel.activar(id_conductor)

        flash(
            'Conductor activado correctamente.',
            'success'
        )

    except Exception as e:
        flash(
            f'Error al activar conductor: {e}',
            'danger'
        )

    return redirect(url_for('conductores.index'))