from asistente import herramientas as h
from asistente.agentes.base import Agente


class Predictor(Agente):
    clave = "predictor"
    nombre = "Predictor"
    tipo = "Especialista (LLM + modelo .joblib)"
    rol = ("Predices si un viaje tendrá alta ocupación con el modelo de machine learning y vigilas su "
           "estado. Para una ruta por nombre, usa listar_rutas y luego predecir_viaje. Para la ruta más "
           "concurrida y su probabilidad usa prediccion_ruta_top. Para saber si el modelo está al día "
           "usa estado_modelo.")
    libreto = ("Identificar ruta, fecha, hora y clima", "Llamar al modelo entrenado",
               "Vigilar su antigüedad y los datos nuevos", "Dejar la probabilidad en la pizarra")
    herramientas = (h.predecir_viaje, h.proximos_viajes, h.listar_rutas, h.top_rutas,
                    h.prediccion_ruta_top, h.estado_modelo)
    palabras = ("predic", "llenara", "llenar", "probab", "pronostic", "proximo", "futuro", "se llena",
                "bus extra", "demanda", "se llene", "modelo", "reentren")
    peso = 2


agente = Predictor()