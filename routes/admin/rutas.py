from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import RutaModel, SedeModel

rutas_bp = Blueprint('rutas', __name__, url_prefix='/admin/rutas')

@rutas_bp.route('/')
def index():
    rutas = RutaModel.get_todas()
    return render_template('admin/rutas/index.html', rutas=rutas)

@rutas_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if request.method == 'POST':
        id_sede_origen = request.form['id_sede_origen']
        id_sede_destino = request.form['id_sede_destino']
        duracion_estimada_hrs = request.form['duracion_estimada_hrs']

        if id_sede_origen == id_sede_destino:
            flash('La sede de origen y la sede de destino no pueden ser la misma.', 'warning')
        else:
            try:
                RutaModel.crear(id_sede_origen, id_sede_destino, duracion_estimada_hrs)
                flash('Ruta registrada correctamente.', 'success')
                return redirect(url_for('rutas.index'))
            except Exception as e:
                flash(f'Error al registrar la ruta: {e}', 'danger')

    sedes = SedeModel.get_todas()
    return render_template('admin/rutas/formulario.html', sedes=sedes)

@rutas_bp.route('/editar/<int:id_ruta>', methods=['GET', 'POST'])
def editar(id_ruta):
    ruta = RutaModel.get_by_id(id_ruta)
    if not ruta:
        flash('Ruta no encontrada.', 'warning')
        return redirect(url_for('rutas.index'))

    if request.method == 'POST':
        id_sede_origen = request.form['id_sede_origen']
        id_sede_destino = request.form['id_sede_destino']
        duracion_estimada_hrs = request.form['duracion_estimada_hrs']

        if id_sede_origen == id_sede_destino:
            flash('La sede de origen y la sede de destino no pueden ser la misma.', 'warning')
        else:
            try:
                RutaModel.actualizar(id_ruta, id_sede_origen, id_sede_destino, duracion_estimada_hrs)
                flash('Ruta actualizada con éxito.', 'success')
                return redirect(url_for('rutas.index'))
            except Exception as e:
                flash(f'Error al actualizar ruta: {e}', 'danger')

    sedes = SedeModel.get_todas()
    return render_template('admin/rutas/formulario.html', ruta=ruta, sedes=sedes)

@rutas_bp.route('/eliminar/<int:id_ruta>', methods=['POST'])
def eliminar(id_ruta):
    try:
        RutaModel.eliminar(id_ruta)
        flash('Ruta eliminada correctamente.', 'info')
    except Exception as e:
        flash('No se puede eliminar la ruta porque está asociada a viajes programados.', 'danger')
    return redirect(url_for('rutas.index'))