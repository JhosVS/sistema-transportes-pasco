# routes/admin/programacion.py
from datetime import datetime
from routes.utils.feriados import es_feriado_peru

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from models import (db, ProgramacionViaje, Vehiculo, Conductor, DetallePasaje, DetalleEncomienda)
from routes.utils.estados_viaje import sincronizar_estados

programacion_bp = Blueprint('programacion', __name__, url_prefix='/admin/programacion')

ESTADOS = ('Programado', 'En Ruta', 'Finalizado', 'Cancelado')
FORMATO_DT = '%Y-%m-%dT%H:%M'


# ============================================================
# HELPERS
# ============================================================
def _parse_dt(texto):
    try:
        return datetime.strptime(texto, FORMATO_DT)
    except (ValueError, TypeError):
        return None


def _leer_formulario(form, viaje):
    """Valida el formulario según el estado del viaje. Retorna (datos, errores)."""
    errores, datos = [], {}
    programado = viaje.estado_viaje == 'Programado'

    # Vehículo y conductor: solo mientras el viaje no haya salido (reemplazos puntuales)
    if programado:
        veh_str = form.get('id_vehiculo', '').strip()
        cond_str = form.get('id_conductor', '').strip()
        datos['id_vehiculo'] = int(veh_str) if veh_str.isdigit() else None
        datos['id_conductor'] = int(cond_str) if cond_str.isdigit() else None

        # El nuevo vehículo debe tener lugar para los pasajeros ya vendidos
        if datos['id_vehiculo']:
            veh = db.session.get(Vehiculo, datos['id_vehiculo'])
            activos = viaje.pasajes_activos
            if not veh:
                errores.append('El vehículo seleccionado no existe.')
            elif activos:
                mayor_asiento = max(p.numero_asiento for p in activos)
                if veh.capacidad_asientos < max(len(activos), mayor_asiento):
                    errores.append(
                        f'El vehículo {veh.placa} tiene {veh.capacidad_asientos} asientos, pero el viaje '
                        f'ya tiene {len(activos)} pasajes (asiento más alto: {mayor_asiento}).')

    datos['es_feriado'] = form.get('es_feriado') == '1'

    # Horas reales (se llenan solas; aquí solo se corrigen)
    if viaje.estado_viaje in ('En Ruta', 'Finalizado'):
        datos['salida_real'] = _parse_dt(form.get('salida_real', ''))
        if not datos['salida_real']:
            errores.append('Ingrese una salida real válida.')
    if viaje.estado_viaje == 'Finalizado':
        datos['llegada_real'] = _parse_dt(form.get('llegada_real', ''))
        if not datos['llegada_real']:
            errores.append('Ingrese una llegada real válida.')
        elif datos.get('salida_real') and datos['llegada_real'] < datos['salida_real']:
            errores.append('La llegada real no puede ser anterior a la salida real.')

    return datos, errores


def _advertencias(viaje, id_vehiculo, id_conductor):
    """Avisos que no bloquean el guardado."""
    avisos = []
    cruce = ProgramacionViaje.query.filter(
        ProgramacionViaje.id_viaje != viaje.id_viaje,
        ProgramacionViaje.estado_viaje != 'Cancelado',
        ProgramacionViaje.salida_programada < viaje.llegada_programada,
        ProgramacionViaje.llegada_programada > viaje.salida_programada,
    )
    if id_vehiculo:
        otro = cruce.filter(ProgramacionViaje.id_vehiculo == id_vehiculo).first()
        if otro:
            avisos.append(f'Aviso: el vehículo ya está asignado al viaje #{otro.id_viaje}, que se cruza en horario.')
    if id_conductor:
        otro = cruce.filter(ProgramacionViaje.id_conductor == id_conductor).first()
        if otro:
            avisos.append(f'Aviso: el conductor ya está asignado al viaje #{otro.id_viaje}, que se cruza en horario.')
        cond = db.session.get(Conductor, id_conductor)
        if cond and cond.licencia_vence < viaje.fecha_salida:
            avisos.append(f'Aviso: la licencia de {cond.nombre_completo} vence el '
                          f'{cond.licencia_vence.strftime("%d/%m/%Y")}, antes de la salida.')
    return avisos

import calendar
from datetime import datetime

# ============================================================
# 1. LISTAR
# ============================================================
@programacion_bp.route('/')
def index():
    sincronizar_estados()

    estado = request.args.get('estado', '').strip()
    id_vehiculo = request.args.get('id_vehiculo', type=int)
    mes_str = request.args.get('mes', '').strip()  # Recibe "YYYY-MM" (ejemplo: "2026-03")

    query = ProgramacionViaje.query

    if estado in ESTADOS:
        query = query.filter(ProgramacionViaje.estado_viaje == estado)
        
    if id_vehiculo:
        query = query.filter(ProgramacionViaje.id_vehiculo == id_vehiculo)

    # Filtrado por Mes y Año
    if mes_str:
        try:
            anyo, mes = map(int, mes_str.split('-'))
            
            # Calcular el primer y último día del mes
            primer_dia = datetime(anyo, mes, 1).date()
            ultimo_dia_num = calendar.monthrange(anyo, mes)[1]
            ultimo_dia = datetime(anyo, mes, ultimo_dia_num).date()

            # Filtrar por fecha_salida o salida_programada
            query = query.filter(
                ProgramacionViaje.fecha_salida >= primer_dia,
                ProgramacionViaje.fecha_salida <= ultimo_dia
            )
        except ValueError:
            flash('Selección de mes inválida.', 'warning')

    viajes = query.order_by(ProgramacionViaje.salida_programada.desc()).limit(200).all()

    ids = [v.id_viaje for v in viajes]
    ocupados = {}
    if ids:
        ocupados = dict(
            db.session.query(DetallePasaje.id_viaje, func.count(DetallePasaje.id_detalle_pasaje))
            .filter(DetallePasaje.id_viaje.in_(ids), DetallePasaje.estado != 'anulado')
            .group_by(DetallePasaje.id_viaje).all()
        )

    conteo = dict(
        db.session.query(ProgramacionViaje.estado_viaje, func.count(ProgramacionViaje.id_viaje))
        .group_by(ProgramacionViaje.estado_viaje).all()
    )

    vehiculos = Vehiculo.query.order_by(Vehiculo.placa).all()

    return render_template(
        'admin/programacion/index.html',
        viajes=viajes, 
        ocupados=ocupados, 
        conteo=conteo, 
        vehiculos=vehiculos,
        estados=ESTADOS, 
        estado_sel=estado, 
        id_vehiculo_sel=id_vehiculo,
        mes_sel=mes_str  # Pasamos mes_sel a la vista para mantener seleccionado el input tipo month
    )

# ============================================================
# 2. DETALLE
# ============================================================
@programacion_bp.route('/<int:id_viaje>')
def detalle(id_viaje):
    sincronizar_estados()

    viaje = db.session.get(ProgramacionViaje, id_viaje)
    if not viaje:
        flash('Viaje no encontrado.', 'warning')
        return redirect(url_for('programacion.index'))

    pasajes = viaje.pasajes_activos
    vehiculo = viaje.vehiculo_efectivo
    encomiendas = [e for e in viaje.encomiendas if e.estado_entrega != 'Perdido']

    return render_template(
        'admin/programacion/detalle.html',
        v=viaje,
        vehiculo=vehiculo,
        conductor=viaje.conductor or (viaje.horario.conductor_default if viaje.horario else None),
        ocupados=len(pasajes),
        capacidad=vehiculo.capacidad_asientos if vehiculo else 0,
        ingresos_pasajes=sum(float(p.precio_pagado) for p in pasajes),
        total_encomiendas=len(encomiendas),
        kg_encomiendas=sum(float(e.peso_kg) for e in encomiendas),
        ahora=datetime.now()
    )


# ============================================================
# 3. EDITAR
# ============================================================
@programacion_bp.route('/editar/<int:id_viaje>', methods=['GET', 'POST'])
def editar(id_viaje):
    viaje = db.session.get(ProgramacionViaje, id_viaje)
    if not viaje:
        flash('Viaje no encontrado.', 'warning')
        return redirect(url_for('programacion.index'))

    if request.method == 'POST':
        datos, errores = _leer_formulario(request.form, viaje)
        if errores:
            for e in errores:
                flash(e, 'warning')
        else:
            try:
                for campo, valor in datos.items():
                    setattr(viaje, campo, valor)
                db.session.commit()
                flash('Viaje actualizado correctamente.', 'success')
                if viaje.estado_viaje == 'Programado':
                    for aviso in _advertencias(viaje, viaje.id_vehiculo, viaje.id_conductor):
                        flash(aviso, 'warning')
                return redirect(url_for('programacion.detalle', id_viaje=id_viaje))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar el viaje: {e}', 'danger')

    # Vehículos: los disponibles, más el que ya tiene asignado
    vehiculos = Vehiculo.query.filter(
        db.or_(Vehiculo.estado == 'Disponible', Vehiculo.id_vehiculo == viaje.id_vehiculo)
    ).order_by(Vehiculo.placa).all()
    conductores = Conductor.query.filter(
        db.or_(Conductor.estado == 'Activo', Conductor.id_conductor == viaje.id_conductor)
    ).order_by(Conductor.apellidos).all()

    return render_template(
        'admin/programacion/formulario.html',
        v=viaje, vehiculos=vehiculos, conductores=conductores,
        form=request.form if request.method == 'POST' else {},
        formato=FORMATO_DT
    )


# ============================================================
# 4. CANCELAR / REACTIVAR
# ============================================================
@programacion_bp.route('/cancelar/<int:id_viaje>', methods=['POST'])
def cancelar(id_viaje):
    viaje = db.session.get(ProgramacionViaje, id_viaje)
    if not viaje:
        flash('Viaje no encontrado.', 'warning')
        return redirect(url_for('programacion.index'))

    if viaje.estado_viaje not in ('Programado', 'En Ruta'):
        flash(f'No se puede cancelar un viaje en estado "{viaje.estado_viaje}".', 'warning')
    else:
        try:
            viaje.estado_viaje = 'Cancelado'
            db.session.commit()
            flash(f'Viaje #{id_viaje} cancelado.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al cancelar el viaje: {e}', 'danger')

    return redirect(url_for('programacion.detalle', id_viaje=id_viaje))


@programacion_bp.route('/reactivar/<int:id_viaje>', methods=['POST'])
def reactivar(id_viaje):
    viaje = db.session.get(ProgramacionViaje, id_viaje)
    if not viaje:
        flash('Viaje no encontrado.', 'warning')
        return redirect(url_for('programacion.index'))

    if viaje.estado_viaje != 'Cancelado' or viaje.salida_programada <= datetime.now():
        flash('Solo se puede reactivar un viaje cancelado cuya salida aún no ha ocurrido.', 'warning')
    else:
        try:
            viaje.estado_viaje = 'Programado'
            viaje.salida_real = None
            viaje.llegada_real = None
            db.session.commit()
            flash(f'Viaje #{id_viaje} reactivado.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al reactivar el viaje: {e}', 'danger')

    return redirect(url_for('programacion.detalle', id_viaje=id_viaje))

# ============================================================
# 5. MARCAR FERIADOS EN VIAJES PROGRAMADOS
# ============================================================
@programacion_bp.route('/marcar-feriados', methods=['POST'])
def marcar_feriados():
    viajes = ProgramacionViaje.query.filter(
        ProgramacionViaje.estado_viaje == 'Programado',
        ProgramacionViaje.es_feriado == False  # noqa: E712
    ).all()

    marcados = 0
    for v in viajes:
        if es_feriado_peru(v.fecha_salida):
            v.es_feriado = True
            marcados += 1

    try:
        db.session.commit()
        flash(f'{marcados} viaje(s) marcados como feriado.', 'success' if marcados else 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al marcar feriados: {e}', 'danger')

    return redirect(url_for('programacion.index'))