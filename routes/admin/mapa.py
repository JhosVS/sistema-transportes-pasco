# routes/admin/mapa.py
import os
from flask import Blueprint, render_template
from database.db import get_connection

mapa_admin_bp = Blueprint('mapa_admin', __name__, url_prefix='/admin/mapa')

@mapa_admin_bp.route('/')
def mostrar_mapa():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Obtener sedes con coordenadas
    cursor.execute("""
        SELECT id_sede, nombre_sede, direccion, latitud, longitud
        FROM sedes
        WHERE latitud IS NOT NULL AND longitud IS NOT NULL
    """)
    sedes = cursor.fetchall()

    # 2. Obtener rutas activas entre sedes
    cursor.execute("""
        SELECT 
            r.id_ruta,
            s1.nombre_sede AS origen,
            s1.latitud AS latitud_origen,
            s1.longitud AS longitud_origen,
            s2.nombre_sede AS destino,
            s2.latitud AS latitud_destino,
            s2.longitud AS longitud_destino
        FROM rutas r
        INNER JOIN sedes s1 ON r.id_sede_origen = s1.id_sede
        INNER JOIN sedes s2 ON r.id_sede_destino = s2.id_sede
    """)
    rutas = cursor.fetchall()

    cursor.close()
    conn.close()

    api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')

    return render_template(
        'admin/mapa.html',
        google_maps_api_key=api_key,
        sedes=sedes,
        rutas=rutas
    )