# asistente/agentes/base.py
from asistente.llm import llamar_llm


class Agente:
    """Estructura común. Todos los agentes comparten el mismo LLM mediante pensar()."""
    clave = ""
    nombre = ""
    rol = ""
    tipo = ""
    libreto = ()
    herramientas = ()
    palabras = ()
    peso = 1

    def pensar(self, ctx, pregunta, extra=""):
        texto, tokens = llamar_llm(pregunta, ctx.base + " " + self.rol + extra, list(self.herramientas))
        ctx.tokens += tokens
        return texto

    def ejecutar(self, ctx, pregunta=None):
        texto = self.pensar(ctx, pregunta or ctx.pregunta)
        if not texto.startswith("No pude generar"):
            ctx.anotar(self, texto)