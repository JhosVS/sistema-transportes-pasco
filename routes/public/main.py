# /routes/public/main.py
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import aliased

from models import DetallePasaje, Horario, ProgramacionViaje, Ruta, Sede, db
from routes.utils.feriados import es_feriado_peru

public_bp = Blueprint('public', __name__)

DIAS = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']


@public_bp.route('/')
def home():
    return render_template('public/index.html')


def _ciudades():
    """Ciudades con rutas activas y, para cada origen, sus destinos posibles."""
    destinos = {}
    for r in Ruta.query.filter_by(activa=True).all():
        if r.origen and r.destino and r.origen.ciudad != r.destino.ciudad:
            destinos.setdefault(r.origen.ciudad, set()).add(r.destino.ciudad)
    todas = sorted(set(destinos) | {d for v in destinos.values() for d in v})
    return todas, {k: sorted(v) for k, v in destinos.items()}


def _viaje_de(h, fecha):
    """Devuelve el viaje del horario en esa fecha; lo crea si no existe."""
    viaje = ProgramacionViaje.query.filter_by(id_horario=h.id_horario, fecha_salida=fecha).first()
    if not viaje:
        salida = datetime.combine(fecha, h.hora_salida)
        horas = float(h.ruta.duracion_estimada_hrs) if h.ruta else 0.0
        viaje = ProgramacionViaje(
            id_horario=h.id_horario, id_vehiculo=h.id_vehiculo_default,
            id_conductor=h.id_conductor_default, fecha_salida=fecha,
            salida_programada=salida, llegada_programada=salida + timedelta(hours=horas),
            precio_pasaje=h.precio_pasaje_base, estado_viaje='Programado',
            es_feriado=es_feriado_peru(fecha))
        db.session.add(viaje)
        db.session.commit()
    return viaje


def _duracion(horas):
    total = int(round(horas * 60))
    return f"{total // 60} h {total % 60:02d} min" if total % 60 else f"{total // 60} h"


@public_bp.route('/buscar')
def buscar_viaje():
    ciudades, destinos = _ciudades()
    origen = request.args.get('origen', '').strip()
    destino = request.args.get('destino', '').strip()
    fecha_str = request.args.get('fecha', '').strip()
    viajes = []

    if origen and destino:
        O, D = aliased(Sede), aliased(Sede)
        horarios = (Horario.query.join(Ruta, Horario.id_ruta == Ruta.id_ruta)
                    .join(O, Ruta.id_sede_origen == O.id_sede)
                    .join(D, Ruta.id_sede_destino == D.id_sede)
                    .filter(O.ciudad == origen, D.ciudad == destino, Horario.estado == 'Activo').all())
        ahora = datetime.now()
        fecha_pedida = None
        if fecha_str:
            try:
                fecha_pedida = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Fecha inválida.', 'warning')
            else:
                if fecha_pedida < ahora.date():
                    flash('Elige una fecha desde hoy.', 'warning')
                    fecha_pedida = None

        for h in horarios:
            dia = DIAS.index(h.dia_semana)
            if fecha_pedida:
                if fecha_pedida.weekday() != dia:
                    continue
                fecha = fecha_pedida
            else:
                fecha = ahora.date() + timedelta(days=(dia - ahora.weekday()) % 7)
            if datetime.combine(fecha, h.hora_salida) <= ahora:
                if fecha_pedida:
                    continue
                fecha += timedelta(days=7)

            viaje = ProgramacionViaje.query.filter_by(id_horario=h.id_horario, fecha_salida=fecha).first()
            if viaje and viaje.estado_viaje != 'Programado':
                continue
            salida = datetime.combine(fecha, h.hora_salida)
            horas = float(h.ruta.duracion_estimada_hrs)
            veh = (viaje.vehiculo if viaje else None) or h.vehiculo_default
            ocupados = (db.session.query(DetallePasaje)
                        .filter(DetallePasaje.id_viaje == viaje.id_viaje, DetallePasaje.estado != 'anulado').count()
                        if viaje else 0)
            viajes.append({
                'id_horario': h.id_horario, 'fecha_iso': fecha.isoformat(),
                'id_viaje': viaje.id_viaje if viaje else None, 'salida': salida,
                'fecha': fecha.strftime('%d/%m/%Y'), 'dia': h.dia_semana,
                'hora': salida.strftime('%H:%M'),
                'llegada': (salida + timedelta(hours=horas)).strftime('%H:%M'),
                'duracion': _duracion(horas),
                'precio': float(viaje.precio_pasaje if viaje else h.precio_pasaje_base),
                'precio_kg': float(h.precio_kg_carga_base), 'terminal': h.ruta.origen.nombre_sede,
                'libres': max(0, (veh.capacidad_asientos if veh else 0) - ocupados)})
        viajes.sort(key=lambda x: x['salida'])
        if not viajes:
            flash('No hay salidas disponibles para ese trayecto o fecha.', 'info')

    return render_template('public/buscar_viaje.html', ciudades=ciudades, destinos=destinos,
                           viajes=viajes, origen=origen, destino=destino, fecha=fecha_str,
                           hoy=datetime.now().strftime('%Y-%m-%d'))

@public_bp.route('/viaje/crear/<int:id_horario>/<fecha>/<destino>')
def abrir_viaje(id_horario, fecha, destino):
    h = db.session.get(Horario, id_horario)
    try:
        f = datetime.strptime(fecha, '%Y-%m-%d').date()
    except ValueError:
        f = None
    if not h or h.estado != 'Activo' or not f or datetime.combine(f, h.hora_salida) <= datetime.now():
        flash('Esa salida ya no está disponible.', 'warning')
        return redirect(url_for('public.buscar_viaje'))
    v = _viaje_de(h, f)
    return redirect(url_for('reservas.asientos' if destino == 'asientos' else 'encomiendas.envio',
                            id_viaje=v.id_viaje))