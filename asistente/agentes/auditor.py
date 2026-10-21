import re

from asistente import herramientas as h
from asistente.agentes.base import Agente


def _num(s):
    s = s.strip(".,")
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        partes = s.split(sep)
        miles = len(partes) > 2 or (len(partes[-1]) == 3 and len(partes[0]) <= 3)
        s = "".join(partes) if miles else partes[0] + "." + partes[1]
    try:
        return float(s)
    except ValueError:
        return None


def _valores(obj, out):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.append(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _valores(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _valores(v, out)


class Auditor(Agente):
    clave = "auditor"
    nombre = "Auditor"
    tipo = "Verificador (reglas, sin IA; corrige con el LLM del autor)"
    libreto = ("Leer lo que escribió cada agente en la pizarra",
               "Comprobar que cada cifra aparezca en lo que devolvieron las herramientas",
               "Si hay cifras dudosas, devolver el texto a su autor para que lo corrija (1 intento)",
               "Si persiste, dejar un aviso visible")

    def auditar(self, texto, pregunta, salidas):
        if not salidas:
            return None
        reales = []
        _valores(salidas, reales)
        de_pregunta = {_num(n) for n in re.findall(r"\d[\d.,]*\d|\d", pregunta)}
        dudosas = []
        for crudo in re.findall(r"\d[\d.,]*\d|\d", texto):
            v = _num(crudo)
            if v is None or v <= 31 or 2000 <= v <= 2100 or v in de_pregunta:
                continue
            tol = 0.51 if v == int(v) else 0.06
            if not any(abs(v - r) <= tol for r in reales):
                dudosas.append(crudo)
        return ("cifras sin respaldo en la base: " + ", ".join(dudosas[:4])) if dudosas else None

    def ejecutar(self, ctx, pregunta=None):
        ctx.traza.append(self.nombre)
        for item in ctx.hallazgos:
            aviso = self.auditar(item["texto"], ctx.pregunta, h.salidas())
            autor = ctx.agentes.get(item["clave"])
            if aviso and autor:
                ctx.traza.append(f"devuelve a {autor.nombre}")
                nuevo = autor.pensar(
                    ctx, ctx.pregunta,
                    extra=f" El Auditor detectó {aviso}. Corrige: usa solo cifras que devuelvan tus "
                          "herramientas, copiadas tal cual.")
                if not nuevo.startswith("No pude generar"):
                    item["texto"] = nuevo
                    aviso = self.auditar(nuevo, ctx.pregunta, h.salidas())
            if aviso:
                ctx.avisos.append(f"{item['agente']}: {aviso}")


agente = Auditor()