# asistente/llm.py
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

# GEMINI_MODEL en el .env permite cambiar de modelo sin tocar el código.
MODELOS = list(dict.fromkeys(m for m in (os.getenv("GEMINI_MODEL"), "gemini-3.5-flash-lite",
                                         "gemini-3.1-flash-lite") if m))
MAX_SALIDA = 500
MAX_LLAMADAS_HERRAMIENTAS = 5

_client = None


class AsistenteOcupado(Exception):
    """Google no respondió (saturado o sin cupo)."""


def _cliente():
    global _client
    if _client is None:
        _client = genai.Client()      # lee GEMINI_API_KEY del entorno
    return _client


def _config(instruccion, herramientas):
    kw = dict(system_instruction=instruccion, max_output_tokens=MAX_SALIDA, temperature=0.3)
    if herramientas:
        kw["tools"] = herramientas
        kw["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=MAX_LLAMADAS_HERRAMIENTAS)
    return types.GenerateContentConfig(**kw)


def llamar_llm(pregunta, instruccion, herramientas=None):
    """Devuelve (texto, tokens_usados). Prueba cada modelo; reintenta solo si el modelo
    pidió una herramienta con nombre inexistente."""
    ultimo = None
    for modelo in MODELOS:
        for _ in range(2):
            try:
                r = _cliente().models.generate_content(
                    model=modelo, contents=pregunta, config=_config(instruccion, herramientas))
                tokens = getattr(r.usage_metadata, "total_token_count", 0) or 0
                return (r.text or "No pude generar una respuesta. Reformula la pregunta."), tokens
            except KeyError as e:                       # herramienta inventada: reintentar
                ultimo = e
                print(f"[LLM] {modelo} pidió una herramienta inexistente: {e}")
            except errors.ServerError as e:             # saturado: siguiente modelo
                ultimo = e
                print(f"[LLM] {modelo} saturado: {e}")
                break
            except errors.ClientError as e:
                ultimo = e
                print(f"[LLM] {modelo} error {e.code}: {e}")
                if e.code == 429:
                    raise AsistenteOcupado("Se alcanzó el límite del plan gratuito. Espera un minuto.")
                break
    raise AsistenteOcupado(f"El asistente no está disponible ahora. Detalle: {ultimo}")