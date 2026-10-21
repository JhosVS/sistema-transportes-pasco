# asistente/registro.py
from asistente.agentes import analista, asesor, auditor, predictor
from asistente.agentes.base import Agente


class _Orquestador(Agente):
    clave = "orquestador"
    nombre = "Orquestador"
    tipo = "Coordinador (reglas, sin IA)"
    libreto = ("Validar la pregunta y revisar cupos y caché",
               "Planificar qué agentes intervienen y en qué orden",
               "Crear la pizarra compartida y activar a los agentes",
               "Cada 15 min: sincronizar estados de viajes",
               "Cada día: dirigir la rutina (Analista, Predictor, Asesor y Auditor) y guardar el informe")


ORQUESTADOR = _Orquestador()
TODOS = [ORQUESTADOR, analista.agente, predictor.agente, asesor.agente, auditor.agente]
POR_CLAVE = {a.clave: a for a in TODOS}