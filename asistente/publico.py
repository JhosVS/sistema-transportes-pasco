# asistente/publico.py
"""Chatbot público: un solo agente, herramientas de información pública únicamente."""
import time
import unicodedata
from datetime import date

from asistente.herramientas import _q, segura
from asistente.llm import AsistenteOcupado, llamar_llm

MAX_PREGUNTA = 200
LIMITE_VISITANTE_DIA = 10
LIMITE_GLOBAL_DIA = 80
CACHE_SEGUNDOS = 900
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

REGLAS = (
    "Eres el asistente virtual de Transportes Pasco, empresa de transporte interprovincial entre Cerro de "
    "Pasco, Lima, Huánuco, Huancayo y Tarma. Ayudas a clientes a conocer horarios, precios y cómo comprar. "
    "Responde en español, amable, en máximo 3 frases. Usa SOLO datos de tus herramientas; si no los tienes, "
    "dilo. Copia horas y precios tal cual. Para comprar pasajes o ver asientos libres, indica que usen "
    "'Consultar Viaje' (buscador del sitio). Para enviar una encomienda, deben elegir un viaje en el buscador "
    "y pulsar 'Enviar encomienda'; para rastrearla, usar 'Rastrear Encomienda' con el DNI del destinatario y la "
    "clave. Nunca pidas ni repitas DNI, teléfonos ni datos personales. No hables de temas internos de la "
    "empresa (ingresos, conductores, flota, sistema). Si la pregunta no trata de viajes, responde que solo "
    "ayudas con viajes y encomiendas. Usa exactamente los nombres de herramienta. Hoy es {dia} {hoy}."
)

_cache, _visitantes, _global = {}, {}, {"fecha": None, "n": 0}


@segura
def ciudades_servidas() -> list:
    """Ciudades a las que llega la empresa y los destinos disponibles desde cada una."""
    filas = _q("""SELECT DISTINCT so.ciudad o, sd.ciudad d FROM rutas r
                  JOIN sedes so ON so.id_sede = r.id_sede_origen
                  JOIN sedes sd ON sd.id_sede = r.id_sede_destino
                  WHERE r.activa = 1 AND so.ciudad <> sd.ciudad ORDER BY so.ciudad, sd.ciudad""")
    out = {}
    for f in filas:
        out.setdefault(f["o"], []).append(f["d"])
    return [{"origen": o, "destinos": d} for o, d in out.items()]


@segura
def horarios_ruta(origen: str, destino: str) -> list:
    """Días y horas de salida, precio del pasaje (soles), duración y terminal de salida para viajar
    entre dos ciudades (ej. origen 'Tarma', destino 'Cerro de Pasco')."""
    filas = _q("""SELECT h.dia_semana, h.hora_salida, h.precio_pasaje_base p, r.duracion_estimada_hrs dur,
                         so.nombre_sede terminal
                  FROM horarios h JOIN rutas r ON r.id_ruta = h.id_ruta
                  JOIN sedes so ON so.id_sede = r.id_sede_origen
                  JOIN sedes sd ON sd.id_sede = r.id_sede_destino
                  WHERE h.estado = 'Activo' AND r.activa = 1 AND so.ciudad LIKE :o AND sd.ciudad LIKE :d
                  ORDER BY FIELD(h.dia_semana,'Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo'),
                           h.hora_salida""",
              o=f"%{origen.strip()}%", d=f"%{destino.strip()}%")
    if not filas:
        return [{"error": "No hay salidas para esa ruta. Usa ciudades_servidas para ver las disponibles."}]
    return [{"dia": f["dia_semana"], "hora": str(f["hora_salida"])[:5], "precio_soles": float(f["p"]),
             "duracion_horas": float(f["dur"]), "terminal_salida": f["terminal"]} for f in filas]


@segura
def tarifa_encomienda(origen: str, destino: str) -> dict:
    """Tarifa por kilo (soles) para enviar una encomienda entre dos ciudades, con mínimo y peso máximo."""
    f = _q("""SELECT MIN(h.precio_kg_carga_base) kg FROM horarios h JOIN rutas r ON r.id_ruta = h.id_ruta
              JOIN sedes so ON so.id_sede = r.id_sede_origen JOIN sedes sd ON sd.id_sede = r.id_sede_destino
              WHERE h.estado = 'Activo' AND so.ciudad LIKE :o AND sd.ciudad LIKE :d""",
           o=f"%{origen.strip()}%", d=f"%{destino.strip()}%")[0]["kg"]
    if f is None:
        return {"error": "No hay servicio de encomiendas para esa ruta."}
    return {"soles_por_kg": float(f), "peso_minimo_kg": 1, "peso_maximo_kg": 20,
            "recojo": "En el terminal de destino, con DNI y clave de recojo"}


HERRAMIENTAS = [ciudades_servidas, horarios_ruta, tarifa_encomienda]


def _norm(t):
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().strip()


def responder(pregunta, visitante):
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"error": "Escribe tu pregunta."}
    if len(pregunta) > MAX_PREGUNTA:
        return {"error": f"Tu pregunta es muy larga (máximo {MAX_PREGUNTA} caracteres)."}
    hoy = date.today()
    if _global["fecha"] != hoy:
        _global.update(fecha=hoy, n=0)
        _visitantes.clear()
    clave = _norm(pregunta)
    en_cache = _cache.get(clave)
    if en_cache and time.time() - en_cache[0] < CACHE_SEGUNDOS:
        return {"respuesta": en_cache[1]}
    if _visitantes.get(visitante, 0) >= LIMITE_VISITANTE_DIA:
        return {"error": "Alcanzaste el límite de preguntas de hoy. Puedes usar el buscador de viajes."}
    if _global["n"] >= LIMITE_GLOBAL_DIA:
        return {"error": "El asistente no está disponible por hoy. Usa el buscador de viajes."}
    try:
        texto, _ = llamar_llm(pregunta, REGLAS.format(hoy=hoy.isoformat(), dia=DIAS[hoy.weekday()]),
                              HERRAMIENTAS)
    except AsistenteOcupado:
        return {"error": "El asistente está ocupado. Intenta de nuevo en un momento."}
    except Exception:
        return {"error": "No pude responder ahora. Intenta de nuevo."}
    _visitantes[visitante] = _visitantes.get(visitante, 0) + 1
    _global["n"] += 1
    if not texto.startswith("No pude generar"):
        _cache[clave] = (time.time(), texto)
    return {"respuesta": texto}