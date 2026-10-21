# asistente/contexto.py
class Contexto:
    """Pizarra compartida: todos los agentes leen y escriben aquí."""

    def __init__(self, pregunta, base, agentes, origen="chat"):
        self.pregunta = pregunta
        self.base = base            # reglas comunes para el LLM
        self.agentes = agentes      # red de agentes (clave -> agente)
        self.origen = origen        # 'chat' o 'rutina'
        self.hallazgos = []         # lo que cada agente aporta
        self.traza = ["Orquestador"]
        self.tokens = 0
        self.avisos = []

    def anotar(self, agente, texto):
        self.hallazgos.append({"clave": agente.clave, "agente": agente.nombre, "texto": texto})
        self.traza.append(agente.nombre)

    def resumen_hallazgos(self):
        return "\n".join(f"- {x['agente']}: {x['texto']}" for x in self.hallazgos)