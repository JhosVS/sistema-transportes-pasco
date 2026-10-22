from datetime import datetime, timedelta

from flask import flash
from sqlalchemy.exc import IntegrityError

from models import DetallePasaje, Horario, ProgramacionViaje, db
from routes.utils.feriados import es_feriado_peru


class Salida:
    """Una salida (horario + fecha). Puede existir o no como viaje en la base."""

    def __init__(self, h, fecha, viaje=None):
        self.h, self.fecha, self.viaje = h, fecha, viaje
        self.salida = datetime.combine(fecha, h.hora_salida)
        self.llegada = self.salida + timedelta(hours=float(h.ruta.duracion_estimada_hrs))
        self.vehiculo = (viaje.vehiculo if viaje else None) or h.vehiculo_default
        self.precio = float(viaje.precio_pasaje) if viaje else float(h.precio_pasaje_base)

    @property
    def capacidad(self):
        return self.vehiculo.capacidad_asientos if self.vehiculo else 40

    def ocupados(self):
        return [p.numero_asiento for p in self.viaje.pasajes_activos] if self.viaje else []

    def info(self):
        r = self.h.ruta
        return {'id_horario': self.h.id_horario, 'fecha_iso': self.fecha.isoformat(),
                'id_viaje': self.viaje.id_viaje if self.viaje else None,
                'fecha': self.fecha, 'hora': self.salida.strftime('%H:%M'),
                'llegada': self.llegada.strftime('%H:%M'), 'precio': self.precio,
                'precio_kg': float(self.h.precio_kg_carga_base), 'capacidad': self.capacidad,
                'origen_ciudad': r.origen.ciudad, 'destino_ciudad': r.destino.ciudad,
                'origen': r.origen.nombre_sede, 'destino': r.destino.nombre_sede}


def resolver(id_horario, fecha_txt, aviso='Esa salida ya no está disponible.'):
    """Valida horario y fecha. Devuelve Salida o None (con mensaje). No escribe en la base."""
    h = db.session.get(Horario, id_horario)
    try:
        fecha = datetime.strptime(fecha_txt, '%Y-%m-%d').date()
    except ValueError:
        fecha = None
    if not h or h.estado != 'Activo' or not fecha or datetime.combine(fecha, h.hora_salida) <= datetime.now():
        flash(aviso, 'warning')
        return None
    viaje = ProgramacionViaje.query.filter_by(id_horario=id_horario, fecha_salida=fecha).first()
    if viaje and viaje.estado_viaje != 'Programado':
        flash(aviso, 'warning')
        return None
    return Salida(h, fecha, viaje)


def crear_viaje(s):
    """Obtiene el viaje o lo crea SIN confirmar (el commit lo hace quien registra el pago)."""
    q = ProgramacionViaje.query.filter_by(id_horario=s.h.id_horario, fecha_salida=s.fecha)
    v = q.first()
    if v:
        s.viaje = v
        return v
    try:
        with db.session.begin_nested():
            v = ProgramacionViaje(
                id_horario=s.h.id_horario, id_vehiculo=s.h.id_vehiculo_default,
                id_conductor=s.h.id_conductor_default, fecha_salida=s.fecha,
                salida_programada=s.salida, llegada_programada=s.llegada,
                precio_pasaje=s.h.precio_pasaje_base, estado_viaje='Programado',
                es_feriado=es_feriado_peru(s.fecha))
            db.session.add(v)
            db.session.flush()
    except IntegrityError:          # otro cliente lo creó al mismo tiempo
        v = q.first()
    s.viaje = v
    return v