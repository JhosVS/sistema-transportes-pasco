import os
from datetime import datetime

from asistente import herramientas as h
from asistente.agentes.base import Agente


class Operaciones(Agente):
    clave = "operaciones"
    nombre = "Operaciones y mantenimiento"
    tipo = "Chat + tarea recurrente"
    grupo = "frecuente"
    rol = ("Revisas alertas y das recomendaciones. Para recomendaciones usa la herramienta "
           "recomendaciones y presenta cada acción con su prioridad, el hallazgo y la acción "
           "sugerida (puedes usar hasta 6 frases).")
    libreto = ("Sincronizar estados de los viajes según la hora",
               "Revisar buses en mantenimiento, licencias y viajes sin asignar",
               "Cruzar con la demanda prevista y sugerir acciones",
               "Vigilar si el modelo necesita reentrenarse")
    herramientas = (h.recomendaciones, h.alertas_operacion, h.estado_flota)
    palabras = ("alerta", "licencia", "venc", "mantenimiento", "sin conductor", "sin vehiculo",
                "problema", "pendiente", "recomend", "sugier", "suger", "que hago", "deberia",
                "accion", "consejo", "que hacer", "hacer esta semana")
    peso = 3

    def tarea(self):
        from routes.utils.estados_viaje import sincronizar_estados
        from routes.admin.predicciones import _cargar
        partes, estado = [f"{sincronizar_estados()} cambio(s) de estado"], "ok"

        acciones = h.recomendaciones().get("acciones", [])
        altas = [a for a in acciones if a["prioridad"] == "alta"]
        partes.append(f"{len(acciones)} acción(es), {len(altas)} alta(s)")
        if altas:
            estado = "alerta"

        _, m = _cargar()
        if m:
            total = int(h._q("SELECT COUNT(*) n FROM v_dataset_ocupacion")[0]["n"])
            nuevos = max(0, total - m["filas"]["total"])
            edad = (datetime.now() - datetime.fromisoformat(m["entrenado_en"])).days
            partes.append(f"modelo de hace {edad} día(s), {nuevos} viaje(s) nuevos")
            if nuevos >= 50 or edad > 30:
                partes.append("conviene reentrenar")
                estado = "alerta"
        return estado, "; ".join(partes)[:500]


agente = Operaciones()