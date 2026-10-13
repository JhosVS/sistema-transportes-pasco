# routes/admin/mapa.py
import os
from flask import Blueprint, render_template
from models import Sede, Ruta

mapa_admin_bp = Blueprint('mapa_admin', __name__, url_prefix='/admin/mapa')


@mapa_admin_bp.route('/')
def mostrar_mapa():
    sedes_db = Sede.query.filter(
        Sede.latitud.isnot(None),
        Sede.longitud.isnot(None),
        Sede.activo == True
    ).all()

    # Convertir sedes a lista de diccionarios con tipos numéricos simples
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

    rutas_db = Ruta.query.filter_by(activa=True).all()

    # Construir lista de rutas con las coordenadas de las sedes de origen y destino
    rutas = []
    for r in rutas_db:
        if r.origen and r.destino and r.origen.latitud and r.origen.longitud and r.destino.latitud and r.destino.longitud:
            rutas.append({
                'id_ruta': r.id_ruta,
                'origen': r.origen.nombre_sede,
                'latitud_origen': float(r.origen.latitud),
                'longitud_origen': float(r.origen.longitud),
                'destino': r.destino.nombre_sede,
                'latitud_destino': float(r.destino.latitud),
                'longitud_destino': float(r.destino.longitud),
            })

    api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')

    return render_template(
        'admin/mapa.html',
        google_maps_api_key=api_key,
        sedes=sedes,
        rutas=rutas
    )