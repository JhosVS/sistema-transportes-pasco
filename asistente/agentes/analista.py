from asistente import herramientas as h
from asistente.agentes.base import Agente


class Analista(Agente):
    clave = "datos"
    nombre = "Analista de datos"
    tipo = "Chat"
    rol = "Analizas ventas, ocupación, rutas, retrasos y flota."
    libreto = ("Identificar el periodo y la métrica pedidos", "Consultar la herramienta adecuada",
               "Redactar la cifra tal como la devuelve la base")
    herramientas = (h.resumen_periodo, h.resumen_rango, h.top_rutas, h.ocupacion_por_dia_semana,
                    h.retraso_por_clima, h.estado_flota)
    palabras = ("ventas", "ingres", "pasajer", "ocupacion", "ruta", "cuantos", "cuanto", "retraso",
                "clima", "flota", "mes", "cancel", "mas se", "dia", "enero", "febrero", "marzo",
                "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
                "diciembre")
    peso = 1


agente = Analista()