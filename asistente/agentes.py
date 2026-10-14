# asistente/agentes.py
import re
import time
import traceback
import unicodedata
from datetime import date

from asistente import herramientas as h
from asistente.llm import AsistenteOcupado, llamar_llm

MAX_PREGUNTA = 300
LIMITE_USUARIO_DIA = 30
LIMITE_TOKENS_DIA = 150_000
CACHE_SEGUNDOS = 600
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

REGLAS = (
    "Eres el asistente de una empresa de transporte interprovincial (Cerro de Pasco, Lima, Huánuco, "
    "Huancayo y Tarma). Responde en español, en máximo 4 frases, con cifras concretas. "
    "Usa SOLO los datos que devuelvan tus herramientas; si no los tienes, dilo. Nunca inventes. "
    "Si el periodo o la ruta pedidos no coinciden con lo que devuelve la herramienta, dilo explícitamente. "
    "Para un mes concreto usa fechas exactas (resumen_rango). "
    "Si preguntan por una ciudad o ruta concreta, la predicción debe ser de ESA ruta (listar_rutas y "
    "predecir_viaje); si no puedes hacerlo, dilo en vez de usar otra ruta. "
    "Si una ciudad tiene varios terminales, responde con el principal y menciona el otro en una frase. "
    "Calcula fechas relativas (este viernes, mañana) a partir de la fecha de hoy. "
    "Si la pregunta no trata del negocio, responde que solo ayudas con el sistema de transporte. "
    "Usa exactamente los nombres de herramienta que se te proporcionan, sin abreviarlos. "
    "Hoy es {dia} {hoy}."
)

AGENTES = {
    "datos": {
        "nombre": "Agente de datos",
        "rol": "Analizas ventas, ocupación, rutas, retrasos y flota.",
        "herramientas": [h.resumen_periodo, h.resumen_rango, h.top_rutas, h.ocupacion_por_dia_semana,
                         h.retraso_por_clima, h.estado_flota],
        "palabras": ["ventas", "ingres", "pasajer", "ocupacion", "ruta", "cuantos", "cuanto", "retraso",
                     "clima", "flota", "mes", "semana", "cancel", "mas se", "dia", "enero", "febrero",
                     "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                     "noviembre", "diciembre"],
        "peso": 1,
    },
    "predictor": {
        "nombre": "Agente predictor",
        "rol": ("Predices si un viaje tendrá alta ocupación con el modelo de machine learning. "
                "Para una ruta por nombre, usa listar_rutas y luego predecir_viaje. "
                "Para la ruta más concurrida y su probabilidad usa prediccion_ruta_top."),
        "herramientas": [h.predecir_viaje, h.proximos_viajes, h.listar_rutas, h.top_rutas,
                         h.prediccion_ruta_top],
        "palabras": ["predic", "llenara", "llenar", "probab", "pronostic", "proximo", "futuro", "se llena",
                     "bus extra", "demanda", "se llene"],
        "peso": 2,
    },
        "operaciones": {
        "nombre": "Agente de operaciones",
        "rol": ("Revisas alertas y das recomendaciones. Para recomendaciones usa la herramienta "
                "recomendaciones y presenta cada acción con su prioridad, el hallazgo y la acción "
                "sugerida (puedes usar hasta 6 frases)."),
        "herramientas": [h.recomendaciones, h.alertas_operacion, h.estado_flota],
        "palabras": ["alerta", "licencia", "venc", "mantenimiento", "sin conductor", "sin vehiculo",
                     "problema", "pendiente", "recomend", "sugier", "suger", "que hago", "deberia",
                     "accion", "consejo", "que hacer",
                     "que me recomiendas", "recomiendas", "hacer esta semana"],
        "peso": 3,
    },
}

_cache = {}
_uso = {}                    # (usuario, fecha) -> preguntas
_tokens = {"fecha": None, "total": 0}


def _norm(t):
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().strip()


def elegir_agentes(pregunta):
    """Coordinador por reglas (cero tokens). Devuelve 1 agente, o 2 si la pregunta es mixta."""
    p = _norm(pregunta)
    puntos = {k: sum(w in p for w in a["palabras"]) * a["peso"] for k, a in AGENTES.items()}
    if re.search(r"\d{1,2}:\d{2}", p):            # menciona una hora: casi seguro es una predicción
        puntos["predictor"] += 3
    orden = sorted(puntos, key=puntos.get, reverse=True)
    primero = orden[0] if puntos[orden[0]] > 0 else "datos"
    segundo = orden[1] if orden[1] != primero else orden[2]

    mixta = any(c in p for c in (" y ", "ademas", "tambien", " e "))
    if mixta and puntos[segundo] > 0:
        if {primero, segundo} == {"datos", "predictor"}:
            return ["predictor"]                  # el predictor ya tiene top_rutas: una sola llamada
        return [primero, segundo]
    return [primero]


def responder(pregunta, usuario):
    pregunta = (pregunta or "").strip()
    if not pregunta:
        return {"error": "Escribe una pregunta."}
    if len(pregunta) > MAX_PREGUNTA:
        return {"error": f"La pregunta es muy larga (máximo {MAX_PREGUNTA} caracteres)."}

    hoy = date.today()
    if _tokens["fecha"] != hoy:
        _tokens.update(fecha=hoy, total=0)
    if _tokens["total"] >= LIMITE_TOKENS_DIA:
        return {"error": "Se alcanzó el cupo diario del asistente. Vuelve a intentar mañana."}
    if _uso.get((usuario, hoy), 0) >= LIMITE_USUARIO_DIA:
        return {"error": f"Llegaste al límite de {LIMITE_USUARIO_DIA} preguntas por día."}

    clave = _norm(pregunta)
    en_cache = _cache.get(clave)
    if en_cache and time.time() - en_cache[0] < CACHE_SEGUNDOS:
        return {**en_cache[1], "cache": True, "tokens": 0}

    base = REGLAS.format(hoy=hoy.isoformat(), dia=DIAS[hoy.weekday()])
    partes, nombres, total = [], [], 0
    for k in elegir_agentes(pregunta):
        ag = AGENTES[k]
        try:
            texto, tokens = llamar_llm(pregunta, base + " " + ag["rol"], ag["herramientas"])
        except AsistenteOcupado as e:
            if partes:
                break
            return {"error": str(e)}
        except Exception as e:
            traceback.print_exc()
            if partes:
                break
            return {"error": f"No se pudo consultar el asistente: {e}"}
        total += tokens
        if texto.startswith("No pude generar"):
            continue
        partes.append(texto)
        nombres.append(ag["nombre"])

    _tokens["total"] += total
    if not partes:
        return {"error": "No pude responder; reformula la pregunta."}

    respuesta = partes[0] if len(partes) == 1 else "\n\n".join(f"{n}: {t}" for n, t in zip(nombres, partes))
    _uso[(usuario, hoy)] = _uso.get((usuario, hoy), 0) + 1
    resp = {"respuesta": respuesta, "agente": " + ".join(nombres), "tokens": total, "cache": False}
    _cache[clave] = (time.time(), resp)
    return resp