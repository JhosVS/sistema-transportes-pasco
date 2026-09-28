# routes/public/mapa.py
from flask import Blueprint, render_template
from database.db import get_connection

mapa_bp = Blueprint('mapa', __name__)

@mapa_bp.route('/mapa')
def ver_mapa():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id_sede, nombre_sede, direccion, latitud, longitud FROM sedes WHERE latitud IS NOT NULL AND longitud IS NOT NULL")
    sedes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('public/mapa.html', sedes=sedes)