from flask import Blueprint, render_template

from models import Ruta, Sede

mapa_admin_bp = Blueprint('mapa_admin', __name__, url_prefix='/admin/mapa')


@mapa_admin_bp.route('/')
def mostrar_mapa():
    sedes = [{'id_sede': s.id_sede, 'nombre_sede': s.nombre_sede, 'ciudad': s.ciudad,
              'direccion': s.direccion, 'altitud': s.altitud_msnm,
              'latitud': float(s.latitud), 'longitud': float(s.longitud)}
             for s in Sede.query.filter(Sede.latitud.isnot(None), Sede.longitud.isnot(None),
                                        Sede.activo == True).all()]  # noqa: E712

    rutas = [{'id_ruta': r.id_ruta, 'origen': r.origen.nombre_sede, 'destino': r.destino.nombre_sede,
              'o': [float(r.origen.latitud), float(r.origen.longitud)],
              'd': [float(r.destino.latitud), float(r.destino.longitud)],
              'km': float(r.distancia_km), 'horas': float(r.duracion_estimada_hrs)}
             for r in Ruta.query.filter_by(activa=True).all()
             if r.origen and r.destino and r.origen.latitud is not None and r.origen.longitud is not None
             and r.destino.latitud is not None and r.destino.longitud is not None]

    return render_template('admin/mapa.html', sedes=sedes, rutas=rutas)