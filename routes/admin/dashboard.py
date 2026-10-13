# routes/admin/dashboard.py
from flask import Blueprint, render_template, session, redirect, url_for
from sqlalchemy import func
from sqlalchemy.orm import aliased
from models import db, ReservaVenta, DetallePasaje, Vehiculo, ProgramacionViaje, Horario, Ruta, Sede

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 1. KPIs principales
    ingresos_totales = db.session.query(
        func.coalesce(func.sum(ReservaVenta.monto_total), 0)
    ).scalar()

    total_pasajes = db.session.query(
        func.count(DetallePasaje.id_detalle_pasaje)
    ).scalar()

    buses_disponibles = db.session.query(
        func.count(Vehiculo.id_vehiculo)
    ).filter(Vehiculo.estado == 'Disponible').scalar()

    total_buses = db.session.query(
        func.count(Vehiculo.id_vehiculo)
    ).scalar()

    kpis = {
        'ingresos_mes': float(ingresos_totales or 0),
        'total_pasajes_mes': total_pasajes or 0,
        'buses_activos': buses_disponibles or 0,
        'total_buses': total_buses or 0,
        'ocupacion_promedio': 0
    }

    # 2. Gráfico 1: Ventas por fecha
    ventas_db = db.session.query(
        func.date_format(ReservaVenta.fecha_emision, '%d %b').label('fecha'),
        func.sum(ReservaVenta.monto_total).label('total')
    ).group_by(
        func.date(ReservaVenta.fecha_emision),
        func.date_format(ReservaVenta.fecha_emision, '%d %b')
    ).order_by(func.date(ReservaVenta.fecha_emision).asc()).limit(14).all()

    labels_ventas = [v.fecha for v in ventas_db] if ventas_db else ['Sin ventas']
    data_ventas = [float(v.total) for v in ventas_db] if ventas_db else [0]

    # 3. Gráfico 2: Estado de la flota de buses
    flota_db = db.session.query(
        Vehiculo.estado,
        func.count(Vehiculo.id_vehiculo).label('cantidad')
    ).group_by(Vehiculo.estado).all()

    labels_flota = [f.estado for f in flota_db] if flota_db else ['Sin buses']
    data_flota = [f.cantidad for f in flota_db] if flota_db else [0]

    # 4. Gráfico 3: Top Rutas con más pasajes vendidos
    SedeOrigen = aliased(Sede)
    SedeDestino = aliased(Sede)

    rutas_db = db.session.query(
        func.concat(SedeOrigen.nombre_sede, ' ➔ ', SedeDestino.nombre_sede).label('ruta'),
        func.count(DetallePasaje.id_detalle_pasaje).label('pasajes_vendidos')
    ).join(ProgramacionViaje, DetallePasaje.id_viaje == ProgramacionViaje.id_viaje)\
     .join(Horario, ProgramacionViaje.id_horario == Horario.id_horario)\
     .join(Ruta, Horario.id_ruta == Ruta.id_ruta)\
     .join(SedeOrigen, Ruta.id_sede_origen == SedeOrigen.id_sede)\
     .join(SedeDestino, Ruta.id_sede_destino == SedeDestino.id_sede)\
     .group_by(Ruta.id_ruta, SedeOrigen.nombre_sede, SedeDestino.nombre_sede)\
     .order_by(func.count(DetallePasaje.id_detalle_pasaje).desc())\
     .limit(5).all()

    labels_rutas = [r.ruta for r in rutas_db] if rutas_db else ['Sin rutas registradas']
    data_rutas = [r.pasajes_vendidos for r in rutas_db] if rutas_db else [0]

    return render_template(
        'admin/dashboard.html',
        kpis=kpis,
        labels_ventas=labels_ventas,
        data_ventas=data_ventas,
        labels_flota=labels_flota,
        data_flota=data_flota,
        labels_rutas=labels_rutas,
        data_rutas=data_rutas
    )