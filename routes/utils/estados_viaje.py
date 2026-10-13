# routes/utils/estados_viaje.py
from datetime import datetime, timedelta
from sqlalchemy import func

from models import db, ProgramacionViaje, IncidenteRuta


def sincronizar_estados(ahora=None):
    """Avanza automáticamente los viajes según la hora actual.

    Programado -> En Ruta      cuando llega la salida programada (salida_real = salida programada)
    En Ruta    -> Finalizado   cuando llega la llegada programada + retrasos de incidentes
                               (llegada_real = esa hora esperada)
    Los viajes Cancelados no se tocan. Retorna la cantidad de cambios aplicados.
    """
    ahora = ahora or datetime.now()

    pendientes = ProgramacionViaje.query.filter(
        ProgramacionViaje.estado_viaje.in_(('Programado', 'En Ruta')),
        ProgramacionViaje.salida_programada <= ahora
    ).all()
    if not pendientes:
        return 0

    retrasos = dict(
        db.session.query(
            IncidenteRuta.id_viaje,
            func.coalesce(func.sum(IncidenteRuta.minutos_retraso_estimado), 0)
        ).filter(
            IncidenteRuta.id_viaje.in_([v.id_viaje for v in pendientes])
        ).group_by(IncidenteRuta.id_viaje).all()
    )

    cambios = 0
    for v in pendientes:
        if v.estado_viaje == 'Programado':
            v.estado_viaje = 'En Ruta'
            if not v.salida_real:
                v.salida_real = v.salida_programada
            cambios += 1

        llegada_esperada = v.llegada_programada + timedelta(minutes=int(retrasos.get(v.id_viaje, 0)))
        if v.estado_viaje == 'En Ruta' and ahora >= llegada_esperada:
            v.estado_viaje = 'Finalizado'
            if not v.llegada_real:
                v.llegada_real = llegada_esperada
            cambios += 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return 0
    return cambios