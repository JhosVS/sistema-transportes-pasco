# generar_datos_simulados.py
"""
Simulador de datos para agencia_transportes (v3).
Genera 2 años de historia a partir de los horarios que existen en la BD.

Uso:  python generar_datos_simulados.py      (con la app Flask detenida)
Requiere: pip install pymysql
"""
import itertools
import random
import unicodedata
from datetime import date, datetime, time, timedelta

import pymysql

# ---------------------------------------------------------------------
# Conexión (ajusta usuario/clave a los de tu .env)
# ---------------------------------------------------------------------
DB = dict(host="localhost", user="app_transportes", password="CambiaEstaClave_456",
          database="agencia_transportes", charset="utf8mb4",
          cursorclass=pymysql.cursors.DictCursor)

# ---------------------------------------------------------------------
# Supuestos del simulador (ajustables)
# ---------------------------------------------------------------------
SEMILLA = 42
DIAS_HISTORIA = 365 * 2
UMBRAL_ALTA = 0.70            # para reportar el balance de clases

ID_SEDE_PASCO = 1
# Buses por corredor (ids de la tabla vehiculo)
FLOTA_CORREDOR = {"Lima": [1, 2, 3, 10], "Huánuco": [4, 9],
                  "Huancayo": [5, 6], "Tarma": [7, 8]}

OCUPACION_BASE = {"Lima": 0.62, "Huánuco": 0.58, "Huancayo": 0.52, "Tarma": 0.42}
FACTOR_DIA = {0: 0.95, 1: 0.85, 2: 0.85, 3: 0.92, 4: 1.10, 5: 1.05, 6: 1.05}   # 0 = lunes
FACTOR_MES = {1: 1.05, 2: 0.90, 3: 0.90, 4: 1.00, 5: 0.95, 6: 0.95,
              7: 1.20, 8: 1.00, 9: 0.95, 10: 1.00, 11: 1.05, 12: 1.20}
FACTOR_FERIADO = 1.30
FACTOR_VISPERA = 1.20
FACTOR_SENTIDO_LIMA = 1.20     # sube a Lima vie/sáb y regresa a Pasco dom/lun
FACTOR_CLIMA = {"despejado": 1.00, "neblina": 0.98, "lluvia": 0.93, "granizo": 0.88}
RUIDO_DEMANDA = 0.15

LLUVIAS, TRANSICION, SECO = [.35, .10, .45, .10], [.55, .15, .25, .05], [.75, .15, .08, .02]
CLIMAS = ["despejado", "neblina", "lluvia", "granizo"]
CLIMA_POR_MES = {12: LLUVIAS, 1: LLUVIAS, 2: LLUVIAS, 3: LLUVIAS,
                 4: TRANSICION, 10: TRANSICION, 11: TRANSICION,
                 5: SECO, 6: SECO, 7: SECO, 8: SECO, 9: SECO}

RETRASO_BASE_CLIMA = {"despejado": 5, "neblina": 15, "lluvia": 30, "granizo": 45}
PROB_INCIDENCIA = {"despejado": 0.02, "neblina": 0.04, "lluvia": 0.08, "granizo": 0.12}
PROB_CANCELACION = {"despejado": 0.004, "neblina": 0.006, "lluvia": 0.02, "granizo": 0.04}
PROB_CORRECTIVO_TRAS_FALLA = 0.25

PROB_NO_SHOW = 0.05
PROB_ANULADO = 0.04
PROB_CLIENTE_NUEVO = 0.30
PROB_SIN_FECHA_NAC = 0.05
PROB_DESCUENTO = 0.12
CANALES, PESOS_CANAL = ["terminal", "web", "app"], [75, 15, 10]
METODOS_TERM, PESOS_TERM = ["efectivo", "yape", "plin", "tarjeta"], [60, 30, 5, 5]
METODOS_DIG, PESOS_DIG = ["yape", "tarjeta", "plin"], [45, 35, 20]

MEDIA_ENCOMIENDAS = {"Lima": 3.0, "Huánuco": 2.0, "Huancayo": 2.0, "Tarma": 1.5}
KM_PREVENTIVO = 10000

FERIADOS_FIJOS = [(1, 1), (5, 1), (6, 29), (7, 28), (7, 29), (8, 30), (10, 8),
                  (11, 1), (12, 8), (12, 25)]
DIAS = {"Lunes": 0, "Martes": 1, "Miercoles": 2, "Jueves": 3,
        "Viernes": 4, "Sabado": 5, "Domingo": 6}

LUGARES = {"Lima": ["Ticlio", "La Oroya", "Chosica", "Junín", "Carhuamayo"],
           "Huánuco": ["Huariaca", "Ambo", "Cayhuayna", "Yanahuanca"],
           "Huancayo": ["Junín", "Ondores", "Jauja", "Concepción"],
           "Tarma": ["Junín", "Ondores", "Carhuamayo", "Palca"]}

NOMBRES_M = ["José", "Luis", "Carlos", "Juan", "Miguel", "Jorge", "Pedro", "Víctor", "Marco", "César",
             "Edgar", "Raúl", "Wilder", "Henry", "Jhon", "Alex", "Fredy", "Elmer", "Ronald", "Daniel",
             "Walter", "Fernando", "Hugo", "Rafael", "Andrés", "Alberto", "Javier", "Diego", "Sergio",
             "Erick", "Edson", "Mateo", "Rubén", "Samuel", "Gregorio", "Jesús"]
NOMBRES_F = ["María", "Rosa", "Carmen", "Ana", "Luz", "Elena", "Sofía", "Gladys", "Milagros", "Yesenia",
             "Sonia", "Berta", "Lucía", "Flor", "Patricia", "Julia", "Teresa", "Nelly", "Marleny", "Dina",
             "Karen", "Diana", "Claudia", "Verónica", "Mónica", "Gabriela", "Yolanda", "Jessica", "Carla",
             "Lorena", "Beatriz", "Valeria", "Natalia", "Isabel", "Paola", "Vanessa", "Ruth", "Elsa"]
APELLIDOS = ["Quispe", "Huamán", "Rojas", "Flores", "Mamani", "Vargas", "Condori", "Castillo", "Salazar",
             "Paredes", "Ramos", "Torres", "Gutiérrez", "Chávez", "Mendoza", "Sánchez", "García", "Díaz",
             "Rivera", "Cárdenas", "Espinoza", "Ponce", "Santos", "Lazo", "Villanueva", "Cóndor", "Poma",
             "Yauri", "Ortiz", "Alvarado", "Rosales", "Zevallos", "Palacios", "Ñahui", "Vílchez", "López",
             "Cruz", "Salinas", "Pérez", "Gonzales", "Morales", "Herrera", "Molina", "Cabrera", "Valencia",
             "Soto", "Reyes", "Vega", "Cáceres", "Delgado", "Ticse", "Hinostroza", "Celis", "Lázaro",
             "Prudencio", "Arias", "Leandro", "Eufracio", "Solís", "Salcedo"]
DESC_INCIDENCIA = {"falla_mecanica": "Falla mecánica en ruta", "accidente": "Accidente en la vía",
                   "bloqueo_via": "Bloqueo de la vía por derrumbe o paro",
                   "clima": "Mal clima en el trayecto", "retraso": "Tráfico o demora en control",
                   "otro": "Incidencia menor"}
DESC_PREVENTIVO = ["Cambio de aceite y filtros", "Revisión de frenos y suspensión", "Cambio de llantas",
                   "Alineamiento y balanceo", "Revisión general y engrase"]
DESC_CORRECTIVO = ["Falla de motor", "Reparación de embrague", "Cambio de batería y alternador",
                   "Falla del sistema de frenos", "Reparación de radiador", "Falla de caja de cambios"]
DESC_ENCOMIENDA = ["Caja de repuestos", "Paquete de ropa", "Documentos", "Encargo de medicinas",
                   "Bolsa de productos", "Costal de papas", "Caja de herramientas", "Sobre"]


# =====================================================================
# Funciones auxiliares
# =====================================================================
def pascua(anio):
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def feriados_del_rango(desde, hasta):
    feriados = set()
    for anio in range(desde.year, hasta.year + 1):
        for mes, dia in FERIADOS_FIJOS:
            feriados.add(date(anio, mes, dia))
        p = pascua(anio)
        feriados.add(p - timedelta(days=3))   # Jueves Santo
        feriados.add(p - timedelta(days=2))   # Viernes Santo
    return feriados


def factor_sentido(corredor, sale_de_pasco, dia_semana):
    if corredor != "Lima":
        return 1.0
    if sale_de_pasco and dia_semana in (4, 5):
        return FACTOR_SENTIDO_LIMA
    if not sale_de_pasco and dia_semana in (6, 0):
        return FACTOR_SENTIDO_LIMA
    return 1.0


def tipo_incidencia(clima):
    if clima in ("lluvia", "granizo"):
        return random.choices(["bloqueo_via", "clima", "falla_mecanica", "retraso", "accidente"],
                              [35, 25, 20, 19, 1])[0]
    return random.choices(["falla_mecanica", "retraso", "otro", "bloqueo_via", "accidente"],
                          [45, 30, 17, 7, 1])[0]


def sin_tildes(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def crear_cliente(clientes, dnis, momento):
    while True:
        dni = str(random.randint(10000000, 79999999))
        if dni not in dnis:
            break
    dnis.add(dni)
    sexo = "M" if random.random() < 0.52 else "F"
    nombre = random.choice(NOMBRES_M if sexo == "M" else NOMBRES_F)
    nacimiento = None
    if random.random() > PROB_SIN_FECHA_NAC:
        edad = int(random.triangular(18, 75, 27))
        nacimiento = momento.date() - timedelta(days=edad * 365 + random.randint(0, 364))
    email = None
    if random.random() < 0.25:
        email = f"{sin_tildes(nombre).lower()}{random.randint(1, 999)}@gmail.com"
    id_cliente = len(clientes) + 1
    clientes[id_cliente] = {
        "id": id_cliente, "dni": dni,
        "nombres": f"{nombre} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}",
        "fecha_nacimiento": nacimiento, "sexo": sexo,
        "telefono": "9" + str(random.randint(10000000, 99999999)),
        "email": email, "creado_en": momento,
    }
    return id_cliente


def elegir_cliente(clientes, pool, dnis, en_este_viaje, momento):
    elegido = None
    if pool and random.random() > PROB_CLIENTE_NUEVO:
        for _ in range(5):
            candidato = random.choice(pool)
            if candidato not in en_este_viaje:
                elegido = candidato
                break
    if elegido is None:
        elegido = crear_cliente(clientes, dnis, momento)
    en_este_viaje.add(elegido)
    pool.append(elegido)
    if momento < clientes[elegido]["creado_en"]:
        clientes[elegido]["creado_en"] = momento
    return elegido


def momento_venta(salida, anticipado):
    media = 4.0 if anticipado else 2.5
    dias_antes = min(14, int(random.expovariate(1 / media)))
    if dias_antes == 0:
        return salida - timedelta(minutes=random.randint(20, 360))
    dia = salida.date() - timedelta(days=dias_antes)
    return datetime.combine(dia, time(random.randint(7, 21), random.randint(0, 59)))


def redondear_medio(x):
    return round(x * 2) / 2


def elegir_libre(lista, salida):
    libres = [x for x in lista if x["libre_desde"] <= salida]
    return min(libres, key=lambda x: x["libre_desde"]) if libres else None


# =====================================================================
# Catálogos desde la BD
# =====================================================================
def cargar_catalogos(cur, desde):
    cur.execute("SELECT id_sede, ciudad FROM sedes")
    ciudad = {f["id_sede"]: f["ciudad"] for f in cur.fetchall()}

    cur.execute("SELECT id_usuario FROM usuarios WHERE id_rol = 4 AND estado = 'Activo' LIMIT 1")
    fila = cur.fetchone()
    boletero = fila["id_usuario"] if fila else None

    antes = datetime.combine(desde, time.min) - timedelta(days=1)
    cur.execute("SELECT id_vehiculo, tipo, capacidad_asientos, capacidad_carga_kg FROM vehiculo")
    vehiculos = {}
    for f in cur.fetchall():
        km = random.randint(60000, 250000)
        vehiculos[f["id_vehiculo"]] = {
            "id": f["id_vehiculo"], "tipo": f["tipo"], "asientos": f["capacidad_asientos"],
            "carga_kg": float(f["capacidad_carga_kg"]), "libre_desde": antes,
            "km": km, "km_ultimo_preventivo": km - random.randint(0, 9000),
        }
    pools = {c: [vehiculos[i] for i in ids if i in vehiculos] for c, ids in FLOTA_CORREDOR.items()}

    cur.execute("SELECT id_conductor FROM conductor WHERE estado = 'Activo'")
    conductores = [{"id": f["id_conductor"], "libre_desde": antes} for f in cur.fetchall()]

    cur.execute("""SELECT h.id_horario, h.dia_semana, h.hora_salida, h.precio_pasaje_base,
                          h.precio_kg_carga_base, r.id_ruta, r.id_sede_origen, r.id_sede_destino,
                          r.distancia_km, r.duracion_estimada_hrs
                   FROM horarios h JOIN rutas r ON r.id_ruta = h.id_ruta
                   WHERE h.estado = 'Activo' AND r.activa = 1""")
    horarios = []
    for f in cur.fetchall():
        sale_de_pasco = f["id_sede_origen"] == ID_SEDE_PASCO
        otra = ciudad[f["id_sede_destino"] if sale_de_pasco else f["id_sede_origen"]]
        if otra not in pools:
            print(f"   (se omite horario {f['id_horario']}: corredor '{otra}' sin flota definida)")
            continue
        horarios.append({
            "id_horario": f["id_horario"], "dia": DIAS[f["dia_semana"]], "hora": f["hora_salida"],
            "precio": float(f["precio_pasaje_base"]), "precio_kg": float(f["precio_kg_carga_base"]),
            "distancia": float(f["distancia_km"]),
            "duracion": int(float(f["duracion_estimada_hrs"]) * 60),
            "origen": f["id_sede_origen"], "corredor": otra, "sale_de_pasco": sale_de_pasco,
        })
    return horarios, pools, vehiculos, conductores, boletero


# =====================================================================
# Simulación
# =====================================================================
def simular(horarios, pools, conductores, boletero, desde, hasta, ahora):
    feriados = feriados_del_rango(desde, hasta)
    climas = {}

    def clima_de(dia):
        if dia not in climas:
            climas[dia] = random.choices(CLIMAS, CLIMA_POR_MES[dia.month])[0]
        return climas[dia]

    clientes, pool, dnis = {}, [], set()
    viajes, reservas, pasajes, encomiendas = [], [], [], []
    incidentes, mantenimientos = [], []
    c_viaje, c_res, c_pas, c_enc, c_inc, c_mant = (itertools.count(1) for _ in range(6))
    stats = {"cancelados_clima": 0, "cancelados_sin_flota": 0, "viajes": 0, "alta": 0}

    def nueva_reserva(id_cliente, momento, monto, estado, id_sede, canal):
        id_res = next(c_res)
        if canal == "terminal":
            metodo = random.choices(METODOS_TERM, PESOS_TERM)[0]
            usuario, sede = boletero, id_sede
        else:
            metodo = random.choices(METODOS_DIG, PESOS_DIG)[0]
            usuario, sede = None, None
        comprobante = random.choices(["boleta", "ticket"], [92, 8])[0]
        reservas.append((id_res, id_cliente, usuario, sede, momento, monto, metodo, canal,
                         comprobante, estado))
        return id_res

    # Plan: todas las salidas, día por día
    plan = []
    dia = desde
    while dia <= hasta:
        for h in horarios:
            if dia.weekday() == h["dia"]:
                plan.append((datetime.combine(dia, time.min) + h["hora"], h))
        dia += timedelta(days=1)
    plan.sort(key=lambda x: (x[0], x[1]["id_horario"]))

    for salida, h in plan:
        fecha = salida.date()
        clima = clima_de(fecha)
        es_fer = fecha in feriados
        es_vis = (fecha + timedelta(days=1)) in feriados
        pico = es_fer or es_vis
        corredor = h["corredor"]
        llegada_prog = salida + timedelta(minutes=h["duracion"])
        precio_viaje = redondear_medio(h["precio"] * (1.10 if pico else 1.0))

        vehiculo = elegir_libre(pools[corredor], salida)
        conductor = elegir_libre(conductores, salida) if vehiculo else None
        sin_flota = vehiculo is None or conductor is None
        cancelado = sin_flota or random.random() < PROB_CANCELACION[clima]

        retraso_salida = retraso_ruta = minutos_inc = 0
        incidencia, grave = None, False
        salida_real = llegada_real = None
        if not cancelado:
            escala = max(0.3, h["duracion"] / 480)
            retraso_salida = max(0, round(random.gauss(5, 6)))
            base = RETRASO_BASE_CLIMA[clima] * escala
            retraso_ruta = max(0, round(random.gauss(base, base * 0.6)))
            if random.random() < PROB_INCIDENCIA[clima]:
                tipo = tipo_incidencia(clima)
                minutos_inc = max(15, round(random.randint(30, 180) * max(escala, 0.4)))
                grave = tipo == "falla_mecanica" and random.random() < PROB_CORRECTIVO_TRAS_FALLA
                incidencia = (tipo, minutos_inc,
                              salida + timedelta(minutes=retraso_salida +
                                                 random.randint(10, max(11, h["duracion"] - 10))))
            salida_real = salida + timedelta(minutes=retraso_salida)
            llegada_real = llegada_prog + timedelta(minutes=retraso_salida + retraso_ruta + minutos_inc)
            if llegada_real > ahora:
                continue

        id_viaje = next(c_viaje)
        stats["viajes"] += 1

        # --- Pasajes (si hubo bus asignado) ---
        if vehiculo is not None:
            asientos = vehiculo["asientos"]
            demanda = (OCUPACION_BASE[corredor] * FACTOR_DIA[fecha.weekday()] * FACTOR_MES[fecha.month]
                       * FACTOR_CLIMA[clima]
                       * factor_sentido(corredor, h["sale_de_pasco"], fecha.weekday())
                       * (FACTOR_FERIADO if es_fer else 1.0) * (FACTOR_VISPERA if es_vis else 1.0)
                       * random.gauss(1, RUIDO_DEMANDA))
            vendidos = round(asientos * min(1.0, max(0.05, demanda)))
            if not cancelado and vendidos / asientos >= UMBRAL_ALTA:
                stats["alta"] += 1
            en_este_viaje = set()
            for nro in random.sample(range(1, asientos + 1), vendidos):
                momento = momento_venta(salida, pico)
                cid = elegir_cliente(clientes, pool, dnis, en_este_viaje, momento)
                c = clientes[cid]
                precio = redondear_medio(precio_viaje * (0.85 if random.random() < PROB_DESCUENTO else 1))
                if cancelado:
                    est_p, est_r = "anulado", "anulada"
                elif random.random() < PROB_NO_SHOW:
                    est_p, est_r = "no_show", "pagada"
                else:
                    est_p, est_r = "abordado", "pagada"
                canal = random.choices(CANALES, PESOS_CANAL)[0]
                id_res = nueva_reserva(cid, momento, precio, est_r, h["origen"], canal)
                pasajes.append((next(c_pas), id_res, id_viaje, nro, c["dni"], c["nombres"],
                                c["fecha_nacimiento"], c["sexo"], precio, est_p))
            if not cancelado:    # pasajes anulados extra (el asiento se revendió)
                for _ in range(round(vendidos * PROB_ANULADO)):
                    momento = momento_venta(salida, pico)
                    cid = elegir_cliente(clientes, pool, dnis, set(), momento)
                    c = clientes[cid]
                    canal = random.choices(CANALES, PESOS_CANAL)[0]
                    id_res = nueva_reserva(cid, momento, precio_viaje, "anulada", h["origen"], canal)
                    pasajes.append((next(c_pas), id_res, id_viaje, random.randint(1, asientos),
                                    c["dni"], c["nombres"], c["fecha_nacimiento"], c["sexo"],
                                    precio_viaje, "anulado"))

        # --- Viaje cancelado ---
        if cancelado:
            stats["cancelados_sin_flota" if sin_flota else "cancelados_clima"] += 1
            viajes.append((id_viaje, h["id_horario"], vehiculo["id"] if vehiculo else None,
                           conductor["id"] if conductor else None, fecha, salida, None,
                           llegada_prog, None, precio_viaje, "Cancelado", clima, int(es_fer)))
            continue

        # --- Encomiendas ---
        carga_total = 0.0
        for _ in range(max(0, round(random.gauss(MEDIA_ENCOMIENDAS[corredor], 1.2)))):
            peso = round(max(0.5, min(120, random.lognormvariate(2.0, 0.9))), 2)
            if carga_total + peso > vehiculo["carga_kg"]:
                break
            carga_total += peso
            momento = salida - timedelta(hours=random.randint(1, 24))
            cid = elegir_cliente(clientes, pool, dnis, set(), momento)
            precio = round(max(5.0, peso * h["precio_kg"]), 1)
            id_res = nueva_reserva(cid, momento, precio, "pagada", h["origen"], "terminal")
            entregada = llegada_real + timedelta(hours=random.randint(1, 48))
            if random.random() < 0.003:
                estado, entregada = "Perdido", None
            elif entregada > ahora:
                estado, entregada = "En transito", None
            else:
                estado = "Entregado"
            encomiendas.append((next(c_enc), id_res, id_viaje,
                                str(random.randint(10000000, 79999999)),
                                f"{random.choice(NOMBRES_M + NOMBRES_F)} {random.choice(APELLIDOS)}",
                                "9" + str(random.randint(10000000, 99999999)),
                                random.choice(DESC_ENCOMIENDA), peso,
                                str(random.randint(100000, 999999)), estado, precio, entregada))

        # --- Incidente ---
        if incidencia:
            tipo, minutos, momento = incidencia
            incidentes.append((next(c_inc), id_viaje, tipo, DESC_INCIDENCIA[tipo],
                               random.choice(LUGARES[corredor]), momento, minutos))

        # --- Bus y conductor quedan ocupados ---
        vehiculo["km"] += round(h["distancia"])
        vehiculo["libre_desde"] = llegada_real + timedelta(minutes=45)
        conductor["libre_desde"] = llegada_real + timedelta(hours=8 if h["duracion"] >= 300 else 1)

        # --- Mantenimiento ---
        if grave:
            dias = random.randint(2, 6)
            mantenimientos.append((next(c_mant), vehiculo["id"], "correctivo",
                                   random.choice(DESC_CORRECTIVO), llegada_real.date(), vehiculo["km"],
                                   round(random.uniform(800, 6000), 2), dias))
            vehiculo["libre_desde"] = llegada_real + timedelta(days=dias)
        elif vehiculo["km"] - vehiculo["km_ultimo_preventivo"] >= KM_PREVENTIVO:
            dias = random.randint(1, 2)
            mantenimientos.append((next(c_mant), vehiculo["id"], "preventivo",
                                   random.choice(DESC_PREVENTIVO), llegada_real.date(), vehiculo["km"],
                                   round(random.uniform(350, 1200), 2), dias))
            vehiculo["km_ultimo_preventivo"] = vehiculo["km"]
            vehiculo["libre_desde"] = llegada_real + timedelta(days=dias)

        viajes.append((id_viaje, h["id_horario"], vehiculo["id"], conductor["id"], fecha, salida,
                       salida_real, llegada_prog, llegada_real, precio_viaje, "Finalizado",
                       clima, int(es_fer)))

    return dict(clientes=clientes, viajes=viajes, reservas=reservas, pasajes=pasajes,
                encomiendas=encomiendas, incidentes=incidentes,
                mantenimientos=mantenimientos, stats=stats)


# =====================================================================
# Guardado
# =====================================================================
def insertar(cur, tabla, columnas, filas, lote=2000):
    sql = (f"INSERT INTO {tabla} ({', '.join(columnas)}) "
           f"VALUES ({', '.join(['%s'] * len(columnas))})")
    for i in range(0, len(filas), lote):
        cur.executemany(sql, filas[i:i + lote])
    print(f"   {tabla:<20} {len(filas):>8,} filas")


def guardar(cur, datos, vehiculos, ahora):
    for tabla in ("incidentes_ruta", "mantenimientos", "detalle_encomiendas",
                  "detalle_pasajes", "reservas_ventas", "programacion_viaje", "clientes"):
        cur.execute(f"DELETE FROM {tabla}")

    clientes = [(c["id"], "DNI", c["dni"], c["nombres"], c["fecha_nacimiento"], c["sexo"],
                 c["telefono"], c["email"], c["creado_en"])
                for c in sorted(datos["clientes"].values(), key=lambda c: c["id"])]
    print("Guardando en la base de datos:")
    insertar(cur, "clientes", ["id_cliente", "tipo_doc", "num_documento", "nombres_razon_social",
                               "fecha_nacimiento", "sexo", "telefono", "email", "creado_en"], clientes)
    insertar(cur, "programacion_viaje",
             ["id_viaje", "id_horario", "id_vehiculo", "id_conductor", "fecha_salida",
              "salida_programada", "salida_real", "llegada_programada", "llegada_real",
              "precio_pasaje", "estado_viaje", "clima", "es_feriado"], datos["viajes"])
    insertar(cur, "reservas_ventas",
             ["id_reserva", "id_cliente", "id_usuario", "id_sede", "fecha_emision", "monto_total",
              "metodo_pago", "canal_venta", "tipo_comprobante", "estado"], datos["reservas"])
    insertar(cur, "detalle_pasajes",
             ["id_detalle_pasaje", "id_reserva", "id_viaje", "numero_asiento", "dni_pasajero",
              "nombre_pasajero", "fecha_nacimiento", "sexo", "precio_pagado", "estado"],
             datos["pasajes"])
    insertar(cur, "detalle_encomiendas",
             ["id_detalle_encomienda", "id_reserva", "id_viaje", "dni_destinatario",
              "nombre_destinatario", "telefono_destinatario", "descripcion_contenido", "peso_kg",
              "clave_recojo", "estado_entrega", "precio_pagado", "entregado_en"], datos["encomiendas"])
    insertar(cur, "incidentes_ruta",
             ["id_incidente", "id_viaje", "tipo_incidente", "descripcion", "lugar_referencial",
              "fecha_hora", "minutos_retraso_estimado"], datos["incidentes"])
    insertar(cur, "mantenimientos",
             ["id_mantenimiento", "id_vehiculo", "tipo", "descripcion", "fecha", "km_al_momento",
              "costo", "dias_inoperativo"], datos["mantenimientos"])

    cur.executemany(
        "UPDATE vehiculo SET kilometraje_actual = %s, estado = %s WHERE id_vehiculo = %s",
        [(v["km"], "Mantenimiento" if v["libre_desde"] > ahora else "Disponible", v["id"])
         for v in vehiculos.values()])


def main():
    resp = input("Esto BORRA viajes, ventas, clientes, encomiendas, incidentes y\n"
                 "mantenimientos actuales y los reemplaza por datos simulados.\n"
                 "(Detén la app Flask.) Escribe SI para continuar: ")
    if resp.strip().upper() != "SI":
        print("Cancelado. No se cambió nada.")
        return

    random.seed(SEMILLA)
    ahora = datetime.now()
    hoy = ahora.date()
    desde, hasta = hoy - timedelta(days=DIAS_HISTORIA), hoy - timedelta(days=1)

    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            horarios, pools, vehiculos, conductores, boletero = cargar_catalogos(cur, desde)
            print(f"Simulando {desde} a {hasta}: {len(horarios)} horarios, "
                  f"{len(vehiculos)} vehículos, {len(conductores)} conductores...")
            datos = simular(horarios, pools, conductores, boletero, desde, hasta, ahora)
            guardar(cur, datos, vehiculos, ahora)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    s = datos["stats"]
    pct = 100 * s["alta"] / max(1, s["viajes"] - s["cancelados_clima"] - s["cancelados_sin_flota"])
    print(f"\nListo. Cancelados por clima: {s['cancelados_clima']}, sin flota: {s['cancelados_sin_flota']}.")
    print(f"Viajes con ocupación >= {UMBRAL_ALTA:.0%}: {pct:.1f}% (ideal entre 30% y 50%).")


if __name__ == "__main__":
    main()