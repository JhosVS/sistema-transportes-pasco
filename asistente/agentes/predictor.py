from asistente import herramientas as h
from asistente.agentes.base import Agente


class Predictor(Agente):
    clave = "predictor"
    nombre = "Predictor"
    tipo = "Especialista (LLM + modelo .joblib)"
    rol = ("Predices si un viaje tendrá alta ocupación con el modelo de machine learning y vigilas su "
           "estado. Para una ruta por nombre, usa listar_rutas y luego predecir_viaje. Para la ruta más "
           "concurrida y su probabilidad usa prediccion_ruta_top. Para saber si el modelo está al día "
           "usa estado_modelo. Para saber qué días de la semana tienen más demanda en una ruta, usa "
           "listar_rutas y luego demanda_por_dia_semana.")
    libreto = ("Identificar ruta, fecha hora", "Llamar al modelo entrenado",
               "Vigilar su antigüedad y los datos nuevos", "Dejar la probabilidad en la pizarra")
    herramientas = (h.predecir_viaje, h.proximos_viajes, h.listar_rutas, h.top_rutas,
                    h.prediccion_ruta_top, h.estado_modelo, h.demanda_por_dia_semana)
    palabras = ("predic", "llenara", "llenar", "probab", "pronostic", "proximo", "futuro", "se llena",
                "bus extra", "demanda", "se llene", "modelo", "reentren", "dia de la semana", "que dia",
                "mas demanda")
    peso = 2


agente = Predictor()