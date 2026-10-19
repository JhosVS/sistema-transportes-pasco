# asistente/orquestador.py
import re
import time
import traceback
import unicodedata
from datetime import date

from sqlalchemy import text

from asistente import herramientas as h
from asistente.llm import AsistenteOcupado, llamar_llm
from asistente.registro import AUDITOR, CONVERSACIONALES, TAREAS
from models import db

MAX_PREGUNTA = 300
LIMITE_USUARIO_DIA = 30
LIMITE_TOKENS_DIA = 150_000
CACHE_SEGUNDOS = 600
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

REGLAS = (
    "Eres el asistente de una empresa de transporte interprovincial (Cerro de Pasco, Lima, Huánuco, "
    "Huancayo y Tarma). Responde en español, en máximo 4 frases, con cifras concretas. "
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

_cache, _uso, _tokens = {}, {}, {"fecha": None, "total": 0}
POR_CLAVE = {a.clave: a for a in CONVERSACIONALES}


def _norm(t):
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().strip()


# ---------------------------------------------------------------- CHAT
def elegir_agentes(pregunta):
    """Coordinación por reglas (cero tokens). Devuelve 1 agente, o 2 si la pregunta es mixta."""
    p = _norm(pregunta)
    puntos = {a.clave: sum(w in p for w in a.palabras) * a.peso for a in CONVERSACIONALES}
    if re.search(r"\d{1,2}:\d{2}", p):
        puntos["predictor"] += 3
    orden = sorted(puntos, key=puntos.get, reverse=True)
    primero = orden[0] if puntos[orden[0]] > 0 else "datos"
    segundo = orden[1] if orden[1] != primero else orden[2]
    mixta = any(c in p for c in (" y ", "ademas", "tambien", " e "))
    if mixta and puntos[segundo] > 0:
        if {primero, segundo} == {"datos", "predictor"}:
            return ["predictor"]
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

    h.iniciar_registro()
    base = REGLAS.format(hoy=hoy.isoformat(), dia=DIAS[hoy.weekday()])
    partes, nombres, total = [], [], 0
    for k in elegir_agentes(pregunta):
        ag = POR_CLAVE[k]
        try:
            texto, tokens = llamar_llm(pregunta, base + " " + ag.rol, list(ag.herramientas))
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
        nombres.append(ag.nombre)

    _tokens["total"] += total
    if not partes:
        return {"error": "No pude responder; reformula la pregunta."}

    respuesta = partes[0] if len(partes) == 1 else "\n\n".join(f"{n}: {t}" for n, t in zip(nombres, partes))
    aviso = AUDITOR.auditar(respuesta, pregunta, h.salidas())
    if aviso:
        respuesta += f"\n\n⚠ Auditor: {aviso}."
    _uso[(usuario, hoy)] = _uso.get((usuario, hoy), 0) + 1
    resp = {"respuesta": respuesta, "agente": " + ".join(nombres + ["Auditor"]),
            "tokens": total, "cache": False}
    _cache[clave] = (time.time(), resp)
    return resp


# ---------------------------------------------------------------- TAREAS
def ejecutar_tarea(clave):
    ag = next(a for a in TAREAS if a.clave == clave)
    try:
        estado, resumen = ag.tarea()
    except Exception as e:
        db.session.rollback()
        estado, resumen = "error", str(e)[:480]
    db.session.execute(text("""INSERT INTO tareas_agente (agente, tarea, estado, resumen)
                               VALUES (:a, :t, :e, :r)"""),
                       {"a": ag.nombre, "t": ag.clave, "e": estado, "r": resumen})
    db.session.commit()
    return {"agente": ag.nombre, "estado": estado, "resumen": resumen}


def ejecutar_grupo(grupo):
    """Ejecuta en orden todos los agentes con tarea de ese grupo ('frecuente' o 'diaria')."""
    return [ejecutar_tarea(a.clave) for a in TAREAS if a.grupo == grupo]


def ultimos(limite=30):
    return [dict(r._mapping) for r in db.session.execute(text(
        "SELECT agente, estado, resumen, ejecutado_en FROM tareas_agente ORDER BY id DESC LIMIT :n"),
        {"n": limite})]