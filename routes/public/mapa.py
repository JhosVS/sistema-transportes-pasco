from flask import Blueprint, render_template
from models import Sede

mapa_bp = Blueprint('mapa', __name__)


@mapa_bp.route('/mapa')
def ver_mapa():
    sedes_db = Sede.query.filter(
        Sede.latitud.isnot(None),
        Sede.longitud.isnot(None),
        Sede.activo == True
    ).all()

    # Convertir a lista de diccionarios para compatibilidad con el filtro `tojson` de Jinja2
    sedes = [
        {
            'id_sede': s.id_sede,
            'nombre_sede': s.nombre_sede,
            'direccion': s.direccion,
            'latitud': float(s.latitud) if s.latitud is not None else None,
            'longitud': float(s.longitud) if s.longitud is not None else None,
        }
        for s in sedes_db
    ]

    return render_template('public/mapa.html', sedes=sedes)