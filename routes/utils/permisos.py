# routes/utils/permisos.py
"""Permisos por rol: prefijo de URL -> roles permitidos. 'admin' siempre pasa."""

OPERATIVOS = {'admin', 'gerente', 'supervisor'}

PERMISOS = {
    '/admin/predicciones':  OPERATIVOS,
    '/admin/asistente':     OPERATIVOS,
    '/admin/horarios':      OPERATIVOS,
    '/admin/rutas':         OPERATIVOS,
    '/admin/mantenimientos': OPERATIVOS,
    '/admin/vehiculos':     OPERATIVOS,
    '/admin/conductores':   OPERATIVOS,
    '/admin/sedes':         {'admin', 'gerente'},
    '/admin/mapa':          {'admin', 'gerente'},
    '/admin/programacion':  OPERATIVOS | {'boletero', 'conductor'},
    '/admin/encomiendas':   OPERATIVOS | {'boletero'},
    '/admin/incidentes':    OPERATIVOS | {'conductor'},
}
# Todo lo demás bajo /admin (dashboard) lo ven todos los roles autenticados.


def puede(rol, ruta):
    if rol == 'admin':
        return True
    for prefijo, roles in PERMISOS.items():
        if ruta.startswith(prefijo):
            return rol in roles
    return True


def puede_ver(rol, prefijo):
    """Para el menú: ¿puede este rol entrar a ese módulo?"""
    return puede(rol, prefijo)