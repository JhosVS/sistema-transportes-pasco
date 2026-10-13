# routes/admin/incidentes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, IncidenteRuta, ProgramacionViaje

incidentes_bp = Blueprint('incidentes', __name__, url_prefix='/admin/incidentes')

# Mapeo de valores ENUM a etiquetas legibles para el usuario
TIPO_INCIDENTE_LABELS = {
    'falla_mecanica': 'Falla Mecánica',
    'accidente': 'Accidente de Tránsito',
    'bloqueo_via': 'Bloqueo de Vía / Protesta',
    'clima': 'Clima / Derrumbe',
    'retraso': 'Retraso Operativo',
    'otro': 'Otro'
}


# ============================================================
# 1. LISTAR INCIDENTES EN RUTA
# ============================================================
@incidentes_bp.route('/')
def listar_incidentes():
    incidentes = IncidenteRuta.query.order_by(IncidenteRuta.fecha_hora.desc()).all()
    return render_template(
        'admin/incidentes/index.html',
        incidentes=incidentes,
        labels=TIPO_INCIDENTE_LABELS
    )


# ============================================================
# 2. REGISTRAR NUEVO INCIDENTE
# ============================================================
@incidentes_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_incidente():
    if request.method == 'POST':
        id_viaje = request.form.get('id_viaje')
        tipo_incidente = request.form.get('tipo_incidente')
        lugar_referencial = request.form.get('lugar_referencial', '').strip()
        minutos_retraso = int(request.form.get('minutos_retraso_estimado', 0))
        descripcion = request.form.get('descripcion', '').strip()

        try:
            nuevo = IncidenteRuta(
                id_viaje=int(id_viaje),
                tipo_incidente=tipo_incidente,
                lugar_referencial=lugar_referencial,
                minutos_retraso_estimado=minutos_retraso,
                descripcion=descripcion
            )
            db.session.add(nuevo)
            db.session.commit()

            flash('Incidente en ruta registrado correctamente.', 'success')
            return redirect(url_for('incidentes.listar_incidentes'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el incidente: {e}', 'danger')

    # Cargar los viajes más recientes para el selector
    viajes = ProgramacionViaje.query.order_by(ProgramacionViaje.fecha_salida.desc()).limit(30).all()
    return render_template('admin/incidentes/nuevo.html', viajes=viajes)