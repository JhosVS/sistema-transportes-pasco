from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash
from models import db, Sede, Ruta, Horario, ProgramacionViaje, DetallePasaje
from routes.utils.feriados import es_feriado_peru

public_bp = Blueprint('public', __name__)

DIAS_PYTHON_A_DB = {0: 'Lunes', 1: 'Martes', 2: 'Miercoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sabado', 6: 'Domingo'}
DIAS_DB_A_PYTHON = {v: k for k, v in DIAS_PYTHON_A_DB.items()}


@public_bp.route('/')
def home():
    return render_template('public/index.html')


@public_bp.route('/buscar', methods=['GET', 'POST'])
def buscar_viaje():
    sedes = Sede.query.filter_by(activo=True).order_by(Sede.nombre_sede.asc()).all()

    # Obtener relaciones de rutas activas para el script de filtrado dinámico en frontend
    rutas_activas = Ruta.query.filter_by(activa=True).all()
    rutas_db = [
        {'id_sede_origen': r.id_sede_origen, 'id_sede_destino': r.id_sede_destino}
        for r in rutas_activas
    ]

    viajes_disponibles = []
    origen_sel = request.form.get('id_origen')
    destino_sel = request.form.get('id_destino')

    if request.method == 'POST' and origen_sel and destino_sel:
        origen_sel, destino_sel = int(origen_sel), int(destino_sel)

        horarios = Horario.query.join(Ruta, Horario.id_ruta == Ruta.id_ruta)\
            .filter(
                Ruta.id_sede_origen == origen_sel,
                Ruta.id_sede_destino == destino_sel,
                Horario.estado == 'Activo'
            ).all()

        if not horarios:
            flash('No hay salidas disponibles para este trayecto.', 'info')
        else:
            ahora = datetime.now()
            fecha_hoy, hora_actual = ahora.date(), ahora.time()

            for h in horarios:
                dia_num = DIAS_DB_A_PYTHON.get(h.dia_semana, 0)
                dias_falta = (dia_num - fecha_hoy.weekday()) % 7
                fecha_proximo = fecha_hoy + timedelta(days=dias_falta)

                hora_salida_obj = h.hora_salida

                if fecha_proximo == fecha_hoy and hora_salida_obj <= hora_actual:
                    fecha_proximo += timedelta(days=7)

                # Buscar o generar la programación del viaje
                viaje = ProgramacionViaje.query.filter_by(
                    id_horario=h.id_horario,
                    fecha_salida=fecha_proximo
                ).first()

                if not viaje:
                    salida_prog = datetime.combine(fecha_proximo, hora_salida_obj)
                    duracion_hrs = float(h.ruta.duracion_estimada_hrs) if h.ruta else 0.0
                    llegada_prog = salida_prog + timedelta(hours=duracion_hrs)

                    viaje = ProgramacionViaje(
                        id_horario=h.id_horario,
                        id_vehiculo=h.id_vehiculo_default,
                        id_conductor=h.id_conductor_default,
                        fecha_salida=fecha_proximo,
                        salida_programada=salida_prog,
                        llegada_programada=llegada_prog,
                        precio_pasaje=h.precio_pasaje_base,
                        estado_viaje='Programado',
                        es_feriado=es_feriado_peru(fecha_proximo)
                    )
                    db.session.add(viaje)
                    db.session.commit()

                if viaje.estado_viaje == 'Cancelado':
                    continue

                # Contar pasajes ocupados (excluyendo anulados)
                ocupados = db.session.query(DetallePasaje)\
                    .filter(DetallePasaje.id_viaje == viaje.id_viaje, DetallePasaje.estado != 'anulado')\
                    .count()

                vehiculo = viaje.vehiculo or h.vehiculo_default
                conductor = viaje.conductor or h.conductor_default

                capacidad = vehiculo.capacidad_asientos if vehiculo else 0
                asientos_libres = capacidad - ocupados

                viajes_disponibles.append({
                    'id_viaje': viaje.id_viaje,
                    'fecha_salida': fecha_proximo.strftime('%d/%m/%Y'),
                    'dia_nombre': h.dia_semana,
                    'hora_salida': hora_salida_obj.strftime('%H:%M') if hora_salida_obj else '',
                    'precio': float(h.precio_pasaje_base),
                    'precio_kg': float(h.precio_kg_carga_base),
                    'duracion': float(h.ruta.duracion_estimada_hrs) if h.ruta else 0,
                    'placa': vehiculo.placa if vehiculo else 'N/A',
                    'bus': f"{vehiculo.marca} {vehiculo.modelo}" if vehiculo else 'N/A',
                    'conductor': conductor.nombre_completo if conductor else 'Por asignar',
                    'asientos_libres': asientos_libres
                })

            viajes_disponibles.sort(key=lambda x: datetime.strptime(x['fecha_salida'], '%d/%m/%Y'))

    return render_template(
        'public/buscar_viaje.html',
        sedes=sedes,
        rutas_json=rutas_db,
        viajes=viajes_disponibles,
        origen_sel=origen_sel,
        destino_sel=destino_sel
    )