from asistente import herramientas as h
from asistente.agentes.base import Agente


class Asesor(Agente):
    clave = "asesor"
    nombre = "Asesor"
    tipo = "Integrador (LLM + reglas de negocio)"
    rol = ("Das recomendaciones accionables. Usa la herramienta recomendaciones e integra lo que "
           "hallaron otros agentes. Presenta cada acción con prioridad, hallazgo y acción sugerida "
           "(hasta 6 frases).")
    libreto = ("Leer los hallazgos que dejaron los otros agentes",
               "Consultar alertas y reglas de negocio (buses, licencias, demanda)",
               "Convertir los datos en acciones sugeridas")
    herramientas = (h.recomendaciones, h.alertas_operacion, h.estado_flota)
    palabras = ("alerta", "licencia", "venc", "mantenimiento", "sin conductor", "sin vehiculo",
                "problema", "pendiente", "recomend", "sugier", "suger", "que hago", "deberia",
                "accion", "consejo", "que hacer", "hacer esta semana")
    peso = 3

    def ejecutar(self, ctx, pregunta=None):
        pregunta = pregunta or ctx.pregunta
        if ctx.hallazgos:       # colabora: parte del trabajo de los demás
            pregunta = (f"{pregunta}\n\nHallazgos de otros agentes (úsalos sin repetirlos):\n"
                        f"{ctx.resumen_hallazgos()}\nCon eso y tus herramientas, da recomendaciones concretas.")
        texto = self.pensar(ctx, pregunta)
        if not texto.startswith("No pude generar"):
            ctx.anotar(self, texto)


agente = Asesor()