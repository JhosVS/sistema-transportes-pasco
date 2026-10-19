# asistente/registro.py
"""Lista única de agentes del sistema."""
from asistente.agentes import analista, auditor, operaciones, predictor
from asistente.agentes.base import Agente

class _Orquestador(Agente):
    clave = "orquestador"
    nombre = "Orquestador"
    tipo = "Coordina (sin IA)"
    libreto = ("Validar la pregunta (largo, cupos por usuario y por día)",
               "Buscar en la caché de 10 minutos",
               "Elegir al agente por palabras clave (cero tokens)",
               "Pasar la respuesta por el Auditor", "Cada día/15 min: ejecutar las tareas de los agentes")


ORQUESTADOR = _Orquestador()
CONVERSACIONALES = [analista.agente, predictor.agente, operaciones.agente]
TAREAS = [operaciones.agente, auditor.agente]
TODOS = [ORQUESTADOR, analista.agente, predictor.agente, operaciones.agente, auditor.agente]
AUDITOR = auditor.agente