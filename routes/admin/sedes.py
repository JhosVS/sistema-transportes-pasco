from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import SedeModel

sedes_bp = Blueprint('sedes', __name__, url_prefix='/admin/sedes')

@sedes_bp.route('/')
def index():
    sedes = SedeModel.get_todas()
    return render_template('admin/sedes/index.html', sedes=sedes)

@sedes_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        nombre_sede = request.form['nombre_sede'].strip()
        direccion = request.form['direccion'].strip()
        latitud = request.form.get('latitud', '').strip()
        longitud = request.form.get('longitud', '').strip()

        try:
            SedeModel.crear(nombre_sede, direccion, latitud, longitud)
            flash('Sede registrada correctamente.', 'success')
            return redirect(url_for('sedes.index'))
        except Exception as e:
            flash(f'Error al registrar sede: {e}', 'danger')

    return render_template('admin/sedes/formulario.html', sede=None)

@sedes_bp.route('/editar/<int:id_sede>', methods=['GET', 'POST'])
def editar(id_sede):
    sede = SedeModel.get_by_id(id_sede)
    if not sede:
        flash('Sede no encontrada.', 'warning')
        return redirect(url_for('sedes.index'))

    if request.method == 'POST':
        nombre_sede = request.form['nombre_sede'].strip()
        direccion = request.form['direccion'].strip()
        latitud = request.form.get('latitud', '').strip()
        longitud = request.form.get('longitud', '').strip()

        try:
            SedeModel.actualizar(id_sede, nombre_sede, direccion, latitud, longitud)
            flash('Sede actualizada con éxito.', 'success')
            return redirect(url_for('sedes.index'))
        except Exception as e:
            flash(f'Error al actualizar sede: {e}', 'danger')

    return render_template('admin/sedes/formulario.html', sede=sede)

@sedes_bp.route('/eliminar/<int:id_sede>', methods=['POST'])
def eliminar(id_sede):
    try:
        SedeModel.eliminar(id_sede)
        flash('Sede eliminada correctamente.', 'info')
    except Exception as e:
        flash('No se puede eliminar la sede porque tiene vehículos, conductores o rutas vinculadas.', 'danger')
    return redirect(url_for('sedes.index'))