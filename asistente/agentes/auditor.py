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
    tipo = "Verifica respuestas + revisión diaria"
    grupo = "diaria"
    libreto = ("Extraer las cifras de la respuesta del asistente",
               "Comprobar que cada una aparezca en lo que devolvió la base (sin usar IA)",
               "Cada día: contar pasajeros por dos caminos distintos y comparar",
               "Detectar viajes realizados sin pasajes")

    def auditar(self, respuesta, pregunta, salidas):
        """Devuelve un aviso si hay cifras que no aparecen en las herramientas (cero tokens)."""
        if not salidas:
            return None
        reales = []
        _valores(salidas, reales)
        de_pregunta = {_num(n) for n in re.findall(r"\d[\d.,]*\d|\d", pregunta)}
        dudosas = []
        for crudo in re.findall(r"\d[\d.,]*\d|\d", respuesta):
            v = _num(crudo)
            if v is None or v <= 31 or 2000 <= v <= 2100 or v in de_pregunta:
                continue
            tol = 0.51 if v == int(v) else 0.06
            if not any(abs(v - r) <= tol for r in reales):
                dudosas.append(crudo)
        if dudosas:
            return "no pude comprobar estas cifras contra la base: " + ", ".join(dudosas[:4])
        return None

    def tarea(self):
        d = h._desde(30)
        a = h._q("""SELECT COALESCE(SUM(pasajes_vendidos),0) n FROM v_dataset_ocupacion
                    WHERE fecha_salida >= :d""", d=d)[0]["n"]
        b = h._q("""SELECT COUNT(*) n FROM detalle_pasajes dp
                    JOIN programacion_viaje pv ON pv.id_viaje = dp.id_viaje
                    WHERE dp.estado <> 'anulado' AND pv.estado_viaje IN ('Finalizado','En Ruta')
                      AND pv.fecha_salida >= :d""", d=d)[0]["n"]
        vacios = h._q("""SELECT COUNT(*) n FROM v_dataset_ocupacion
                         WHERE fecha_salida >= :d AND pasajes_vendidos = 0""", d=d)[0]["n"]
        problemas = []
        if int(a) != int(b):
            problemas.append(f"la vista cuenta {int(a)} pasajeros y el detalle {int(b)}")
        if vacios:
            problemas.append(f"{int(vacios)} viaje(s) realizados sin ningún pasaje")
        if problemas:
            return "alerta", "Inconsistencias: " + "; ".join(problemas) + "."
        return "ok", f"Cifras coherentes: {int(a)} pasajeros en 30 días en ambas fuentes."


agente = Auditor()