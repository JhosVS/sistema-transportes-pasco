# asistente/agentes/base.py
class Agente:
    """Estructura común de todos los agentes."""
    clave = ""
    nombre = ""
    rol = ""                 # instrucción que recibe el LLM (solo agentes de chat)
    libreto = ()             # pasos que sigue el agente
    herramientas = ()        # funciones que puede usar el LLM
    palabras = ()            # palabras clave con las que el orquestador lo elige
    peso = 1
    grupo = None             # 'frecuente' | 'diaria' si tiene tarea recurrente
    tipo = ""                # texto para mostrar en la página

    def tarea(self):
        """Tarea recurrente. Devuelve (estado, resumen)."""
        raise NotImplementedError