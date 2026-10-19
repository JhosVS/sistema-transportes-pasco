from asistente import herramientas as h
from asistente.agentes.base import Agente


class Predictor(Agente):
    clave = "predictor"
    nombre = "Predictor"
    tipo = "Chat"
    rol = ("Predices si un viaje tendrá alta ocupación con el modelo de machine learning. "
           "Para una ruta por nombre, usa listar_rutas y luego predecir_viaje. "
           "Para la ruta más concurrida y su probabilidad usa prediccion_ruta_top.")
    libreto = ("Identificar ruta, fecha, hora y clima", "Llamar al modelo entrenado (.joblib)",
               "Informar la probabilidad de alta ocupación")
    herramientas = (h.predecir_viaje, h.proximos_viajes, h.listar_rutas, h.top_rutas,
                    h.prediccion_ruta_top)
    palabras = ("predic", "llenara", "llenar", "probab", "pronostic", "proximo", "futuro", "se llena",
                "bus extra", "demanda", "se llene")
    peso = 2


agente = Predictor()