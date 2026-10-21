# asistente/orquestador.py
import re
import time
import traceback
import unicodedata
from datetime import date

from sqlalchemy import text

from asistente import herramientas as h
from asistente.contexto import Contexto
from asistente.llm import AsistenteOcupado
from asistente.registro import POR_CLAVE, TODOS
from models import db

MAX_PREGUNTA = 300
LIMITE_USUARIO_DIA = 30
LIMITE_TOKENS_DIA = 150_000
CACHE_SEGUNDOS = 600
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

REGLAS = (
    "Eres parte de un equipo de agentes de una empresa de transporte interprovincial (Cerro de Pasco, "
    "Lima, Huánuco, Huancayo y Tarma). Responde en español, en máximo 4 frases, con cifras concretas. "
    "Usa SOLO los datos que devuelvan tus herramientas; si no los tienes, dilo. Nunca inventes. "
    "Copia las cifras exactamente como las devuelven las herramientas, sin reformatearlas. "
    "Si el periodo o la ruta pedidos no coinciden con lo que devuelve la herramienta, dilo explícitamente. "
    "Para un mes concreto usa fechas exactas (resumen_rango). "
    "Si preguntan por una ciudad o ruta concreta, la predicción debe ser de ESA ruta (listar_rutas y "
    "predecir_viaje); si no puedes hacerlo, dilo en vez de usar otra ruta. "
    "Si la fecha y hora pedidas ya pasaron, usa la siguiente ocurrencia futura. "
    "Si una ciudad tiene varios terminales, responde con el principal y menciona el otro en una frase. "
    "Calcula fechas relativas (este viernes, mañana) a partir de la fecha de hoy. "
    "Si la pregunta no trata del negocio, responde que solo ayudas con el sistema de transporte. "
    "Usa exactamente los nombres de herramienta que se te proporcionan, sin abreviarlos. "
    "Hoy es {dia} {hoy}."
)

PASOS_RUTINA = [
    ("datos", "Resume en 3 frases los últimos 7 días: viajes, pasajeros, ocupación e ingresos."),
    ("predictor", "Informa el estado del modelo predictivo y la probabilidad de los próximos viajes."),
    ("asesor", "Da las recomendaciones de la semana."),
    ("auditor", None),
]

_cache, _uso, _tokens = {}, {}, {"fecha": None, "total": 0}


def _norm(t):
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().strip()


def _contexto(pregunta, origen="chat"):
    h.iniciar_registro()
    hoy = date.today()
    base = REGLAS.format(hoy=hoy.isoformat(), dia=DIAS[hoy.weekday()])
    return Contexto(pregunta, base, POR_CLAVE, origen)


# ------------------------------------------------------------ PLANIFICACIÓN
def planificar(pregunta):
    """Decide qué agentes intervienen y en qué orden (reglas, cero tokens). El Auditor va siempre al final."""
    p = _norm(pregunta)
    candidatos = ("datos", "predictor", "asesor")
    puntos = {k: sum(w in p for w in POR_CLAVE[k].palabras) * POR_CLAVE[k].peso for k in candidatos}
    if re.search(r"\d{1,2}:\d{2}", p):
        puntos["predictor"] += 3
    orden = sorted(puntos, key=puntos.get, reverse=True)
    primero = orden[0] if puntos[orden[0]] > 0 else "datos"
    mixta = any(c in p for c in (" y ", "ademas", "tambien", " e "))
    plan = [primero]
    if mixta and primero != "asesor" and puntos["asesor"] > 0:
        plan.append("asesor")                       # el Asesor integra lo que hallaron los demás
    elif mixta and {primero, orden[1]} == {"datos", "predictor"}:
        plan = ["predictor"]                        # el Predictor ya tiene top_rutas
    return plan + ["auditor"]


# ------------------------------------------------------------ CHAT
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

    ctx = _contexto(pregunta)
    try:
        for k in planificar(pregunta):
            POR_CLAVE[k].ejecutar(ctx)
    except AsistenteOcupado as e:
        if not ctx.hallazgos:
            return {"error": str(e)}
    except Exception as e:
        traceback.print_exc()
        if not ctx.hallazgos:
            return {"error": f"No se pudo consultar el asistente: {e}"}

    _tokens["total"] += ctx.tokens
    if not ctx.hallazgos:
        return {"error": "No pude responder; reformula la pregunta."}

    respuesta = ctx.hallazgos[-1]["texto"]
    if ctx.avisos:
        respuesta += "\n\n⚠ Auditor: " + "; ".join(ctx.avisos) + "."
    _uso[(usuario, hoy)] = _uso.get((usuario, hoy), 0) + 1
    resp = {"respuesta": respuesta, "agente": " → ".join(ctx.traza), "tokens": ctx.tokens, "cache": False}
    _cache[clave] = (time.time(), resp)
    return resp


# ------------------------------------------------------------ TAREAS PROGRAMADAS
def _registrar(agente, tarea, estado, resumen):
    db.session.execute(text("""INSERT INTO tareas_agente (agente, tarea, estado, resumen)
                               VALUES (:a, :t, :e, :r)"""),
                       {"a": agente, "t": tarea, "e": estado, "r": resumen[:4000]})
    db.session.commit()


def sincronizar():
    """Cada 15 min: tarea de sistema que el Orquestador ejecuta (mantiene los datos al día)."""
    try:
        from routes.utils.estados_viaje import sincronizar_estados
        n = sincronizar_estados()
        estado, resumen = "ok", f"{n} cambio(s) de estado aplicados."
    except Exception as e:
        db.session.rollback()
        estado, resumen = "error", str(e)[:480]
    _registrar("Orquestador", "sincronizar", estado, resumen)
    return {"agente": "Orquestador", "estado": estado, "resumen": resumen}


def rutina_diaria():
    """Cada día: el Orquestador activa la red completa y guarda un informe."""
    try:
        sincronizar()
        ctx = _contexto("Informe diario de operación", origen="rutina")
        for k, preg in PASOS_RUTINA:
            POR_CLAVE[k].ejecutar(ctx, preg)
        hay_alta = any(isinstance(s, dict) and any(a.get("prioridad") == "alta" for a in s.get("acciones", []))
                       for s in h.salidas())
        estado = "alerta" if (ctx.avisos or hay_alta) else "ok"
        cuerpo = " | ".join(f"{x['agente']}: {x['texto']}" for x in ctx.hallazgos)
        if ctx.avisos:
            cuerpo += " | ⚠ " + "; ".join(ctx.avisos)
        resumen = " → ".join(ctx.traza) + "\n" + cuerpo
    except Exception as e:
        db.session.rollback()
        estado, resumen = "error", str(e)[:480]
    _registrar("Orquestador (rutina)", "rutina_diaria", estado, resumen)
    return {"agente": "Red de agentes", "estado": estado, "resumen": resumen}


def ultimos(limite=20):
    return [dict(r._mapping) for r in db.session.execute(text(
        "SELECT agente, estado, resumen, ejecutado_en FROM tareas_agente ORDER BY id DESC LIMIT :n"),
        {"n": limite})]