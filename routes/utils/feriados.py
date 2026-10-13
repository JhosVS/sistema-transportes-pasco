# routes/utils/feriados.py
from datetime import date, timedelta

# Feriados nacionales de fecha fija en Perú (mes, día)
FERIADOS_FIJOS = {
    (1, 1),    # Año Nuevo
    (5, 1),    # Día del Trabajo
    (6, 7),    # Batalla de Arica y Día de la Bandera
    (6, 29),   # San Pedro y San Pablo
    (7, 23),   # Día de la Fuerza Aérea del Perú
    (7, 28),   # Fiestas Patrias
    (7, 29),   # Fiestas Patrias
    (8, 6),    # Batalla de Junín
    (8, 30),   # Santa Rosa de Lima
    (10, 8),   # Combate de Angamos
    (11, 1),   # Todos los Santos
    (12, 8),   # Inmaculada Concepción
    (12, 9),   # Batalla de Ayacucho
    (12, 25),  # Navidad
}


def _domingo_de_pascua(anio):
    """Algoritmo de Meeus/Jones/Butcher (calendario gregoriano)."""
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def es_feriado_peru(fecha):
    """True si la fecha es feriado nacional (fijo, o Jueves/Viernes Santo)."""
    if (fecha.month, fecha.day) in FERIADOS_FIJOS:
        return True
    pascua = _domingo_de_pascua(fecha.year)
    return fecha in (pascua - timedelta(days=3), pascua - timedelta(days=2))