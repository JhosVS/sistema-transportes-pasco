# generar_datos_simulados.py
"""
Simulador de datos para agencia_transportes (sin clima ni combustible).
- Si faltan los datos base (sedes, rutas, horarios, buses, conductores, usuarios), los crea.
- Genera 2 años de historia y los viajes programados de los próximos días.
- Usa las credenciales del .env (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_SSL_CA).

Uso (desde la raíz, con Flask detenido):  python generar_datos_simulados.py
"""
import itertools
import os
import random
import unicodedata
from datetime import date, datetime, time, timedelta

import bcrypt
import pymysql
from dotenv import load_dotenv

from routes.utils.feriados import es_feriado_peru

load_dotenv()

# ---------------------------------------------------------------------
# Supuestos (ajustables)
# ---------------------------------------------------------------------
SEMILLA = 42
DIAS_HISTORIA = 365 * 2
DIAS_FUTUROS = 0             # viajes "Programado" sin pasajes, para probar predicciones
UMBRAL_ALTA = 0.70
ID_SEDE_PASCO = 1

FLOTA_CORREDOR = {"Lima": [1, 2, 3, 10], "Huánuco": [4, 9], "Huancayo": [5, 6], "Tarma": [7, 8]}
OCUPACION_BASE = {"Lima": 0.62, "Huánuco": 0.58, "Huancayo": 0.52, "Tarma": 0.42}
FACTOR_DIA = {0: 0.95, 1: 0.85, 2: 0.85, 3: 0.92, 4: 1.10, 5: 1.05, 6: 1.05}
FACTOR_MES = {1: 1.05, 2: 0.90, 3: 0.90, 4: 1.00, 5: 0.95, 6: 0.95,
              7: 1.20, 8: 1.00, 9: 0.95, 10: 1.00, 11: 1.05, 12: 1.20}
FACTOR_FERIADO, FACTOR_VISPERA, FACTOR_SENTIDO_LIMA = 1.30, 1.20, 1.20
RUIDO_DEMANDA = 0.15

PROB_CANCELACION = 0.01
PROB_INCIDENCIA = 0.05
PROB_CORRECTIVO_TRAS_FALLA = 0.25
PROB_NO_SHOW, PROB_ANULADO = 0.05, 0.04
PROB_CLIENTE_NUEVO, PROB_SIN_FECHA_NAC, PROB_DESCUENTO = 0.30, 0.05, 0.12
CANALES, PESOS_CANAL = ["terminal", "web", "app"], [75, 15, 10]
METODOS_TERM, PESOS_TERM = ["efectivo", "yape", "plin", "tarjeta"], [60, 30, 5, 5]
METODOS_DIG, PESOS_DIG = ["yape", "tarjeta", "plin"], [45, 35, 20]
MEDIA_ENCOMIENDAS = {"Lima": 3.0, "Huánuco": 2.0, "Huancayo": 2.0, "Tarma": 1.5}
KM_PREVENTIVO = 10000
DIAS = {"Lunes": 0, "Martes": 1, "Miercoles": 2, "Jueves": 3, "Viernes": 4, "Sabado": 5, "Domingo": 6}

LUGARES = {"Lima": ["Ticlio", "La Oroya", "Chosica", "Junín", "Carhuamayo"],
           "Huánuco": ["Huariaca", "Ambo", "Cayhuayna", "Yanahuanca"],
           "Huancayo": ["Junín", "Ondores", "Jauja", "Concepción"],
           "Tarma": ["Junín", "Ondores", "Carhuamayo", "Palca"]}
TIPOS_INC = ["falla_mecanica", "retraso", "otro", "bloqueo_via", "accidente"]
PESOS_INC = [45, 30, 17, 7, 1]
DESC_INC = {"falla_mecanica": "Falla mecánica en ruta", "accidente": "Accidente en la vía",
            "bloqueo_via": "Bloqueo de la vía por derrumbe o paro", "retraso": "Tráfico o demora en control",
            "otro": "Incidencia menor"}
DESC_PREV = ["Cambio de aceite y filtros", "Revisión de frenos y suspensión", "Cambio de llantas",
             "Alineamiento y balanceo", "Revisión general y engrase"]
DESC_CORR = ["Falla de motor", "Reparación de embrague", "Cambio de batería y alternador",
             "Falla del sistema de frenos", "Reparación de radiador", "Falla de caja de cambios"]
DESC_ENC = ["Caja de repuestos", "Paquete de ropa", "Documentos", "Encargo de medicinas",
            "Bolsa de productos", "Costal de papas", "Caja de herramientas", "Sobre"]

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


# =====================================================================
# Conexión
# =====================================================================
def conectar():
    cfg = dict(host=os.getenv("DB_HOST", "localhost"), user=os.getenv("DB_USER", "root"),
               password=os.getenv("DB_PASSWORD", ""), database=os.getenv("DB_NAME", "agencia_transportes"),
               port=int(os.getenv("DB_PORT", 3306)), charset="utf8mb4",
               cursorclass=pymysql.cursors.DictCursor)
    if os.getenv("DB_SSL_CA"):
        cfg["ssl"] = {"ca": os.getenv("DB_SSL_CA")}
    return pymysql.connect(**cfg)


# =====================================================================
# Datos base (solo si faltan)
# =====================================================================
def _hash(clave):
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt()).decode()


def sembrar_base(cur):
    def vacia(tabla):
        cur.execute(f"SELECT COUNT(*) n FROM {tabla}")
        return cur.fetchone()["n"] == 0

    if vacia("sedes"):
        cur.executemany("""INSERT INTO sedes (id_sede, nombre_sede, ciudad, departamento, direccion,
                           altitud_msnm, latitud, longitud) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", [
            (1, 'Terminal Terrestre de Chaupimarca', 'Cerro de Pasco', 'Pasco', 'Av. La Plata S/N, Barrio Chaupimarca', 4330, -10.6867536, -76.2566565),
            (3, 'Terminal Pariachi Ate', 'Lima', 'Lima', 'Av. Nicolás Ayllón', 100, -11.9959883, -76.8338787),
            (4, 'Agencia La Victoria / Terminal Yerbateros', 'Lima', 'Lima', 'Av. Nicolás Arriola / Av. Circunvalación', 150, -12.0670149, -77.0325008),
            (5, 'Agencia TEPSA Huanuco', 'Huánuco', 'Huánuco', '402 Jirón Huallayco', 1900, -9.9337256, -76.2459845),
            (6, 'Agencia Terminal Huancayo', 'Huancayo', 'Junín', 'Av. Ferrocarril 1500', 3259, -12.0653, -75.2049),
            (7, 'Agencia Terminal Tarma', 'Tarma', 'Junín', 'Av. Vienrich S/N', 3050, -11.4189, -75.6895)])
        print("   sedes creadas")
    if vacia("roles"):
        cur.executemany("INSERT INTO roles (id_rol, codigo, nombre, descripcion) VALUES (%s,%s,%s,%s)", [
            (1, 'admin', 'Administrador', 'Acceso total'), (2, 'gerente', 'Gerente', 'Reportes y tarifas'),
            (3, 'supervisor', 'Supervisor', 'Programación de viajes'),
            (4, 'boletero', 'Boletero', 'Venta de boletos y encomiendas'),
            (5, 'conductor', 'Conductor', 'Consulta de sus viajes')])
    if vacia("usuarios"):
        cur.executemany("""INSERT INTO usuarios (id_rol, id_sede, username, email, password_hash, nombres,
                           apellidos, debe_cambiar_clave) VALUES (%s,%s,%s,%s,%s,%s,%s,0)""", [
            (1, 1, 'admin', 'admin@transportes.com', _hash('Admin123'), 'Administrador', 'Principal'),
            (4, 1, 'boletero1', 'boletero1@transportes.com', _hash('Boletero123'), 'Rosa Elena', 'Mendoza Ticse')])
        print("   usuarios creados: admin / Admin123  y  boletero1 / Boletero123")
    if vacia("vehiculo"):
        cur.executemany("""INSERT INTO vehiculo (id_vehiculo, placa, marca, modelo, anio, color, tipo,
                           capacidad_asientos, capacidad_carga_kg, kilometraje_actual)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0)""", [
            (1, 'C1A-750', 'Mercedes-Benz', 'O-500R', 2018, 'Azul/Blanco', 'bus', 44, 1200),
            (2, 'B8M-910', 'Volvo', 'B450R', 2020, 'Rojo/Plata', 'bus', 48, 1500),
            (3, 'F5T-320', 'Scania', 'K360', 2019, 'Blanco', 'bus', 40, 1000),
            (4, 'A2K-110', 'Hyundai', 'Universe', 2017, 'Gris', 'bus', 36, 800),
            (5, 'D4H-205', 'Volvo', 'B450R', 2021, 'Blanco/Verde', 'bus', 46, 1400),
            (6, 'G7P-640', 'Mercedes-Benz', 'O-500RS', 2019, 'Azul', 'bus', 44, 1200),
            (7, 'H3L-118', 'Toyota', 'Hiace', 2021, 'Blanco', 'minivan', 15, 400),
            (8, 'J9R-452', 'Toyota', 'Hiace', 2022, 'Plata', 'minivan', 15, 400),
            (9, 'K2N-873', 'Scania', 'K360', 2020, 'Rojo/Blanco', 'bus', 40, 1000),
            (10, 'L6V-295', 'Volvo', 'B8R', 2018, 'Gris/Azul', 'bus', 42, 1100)])
        print("   vehículos creados")
    if vacia("conductor"):
        cur.executemany("""INSERT INTO conductor (id_conductor, dni, nombres, apellidos, telefono,
                           licencia_conducir, licencia_categoria, licencia_vence, fecha_ingreso)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", [
            (1, '45892134', 'Juan Carlos', 'Pérez Quispe', '963852741', 'Q45892134', 'A-IIIc', '2028-06-30', '2021-03-15'),
            (2, '70123456', 'Ronaldo', 'Espinoza Ramos', '987654321', 'E70123456', 'A-IIIc', '2027-09-20', '2022-01-10'),
            (3, '10293847', 'Wilder', 'López Tacuri', '951753852', 'L10293847', 'A-IIIc', '2027-11-05', '2022-08-20'),
            (4, '25364758', 'Héctor', 'Chávez Meléndez', '912345678', 'C25364758', 'A-IIIc', '2028-02-14', '2023-05-01'),
            (5, '41122334', 'Pedro Luis', 'Cóndor Yauri', '944112233', 'C41122334', 'A-IIIb', '2028-03-10', '2020-02-01'),
            (6, '42233445', 'Hugo Armando', 'Poma Salazar', '955223344', 'P42233445', 'A-IIIc', '2028-07-22', '2021-06-15'),
            (7, '43344556', 'Walter', 'Mamani Quispe', '966334455', 'M43344556', 'A-IIIb', '2027-12-12', '2022-03-03'),
            (8, '44455667', 'Edgar Ronald', 'Lazo Vargas', '977445566', 'L44455667', 'A-IIIb', '2029-01-18', '2023-01-20'),
            (9, '46677889', 'Santos', 'Ccori Paredes', '988556677', 'C46677889', 'A-IIIb', '2028-10-05', '2023-09-11'),
            (10, '47788990', 'Alberto', 'Hinostroza Celis', '999667788', 'H47788990', 'A-IIIc', '2029-04-30', '2024-02-05')])
        print("   conductores creados")
    if vacia("rutas"):
        cur.executemany("""INSERT INTO rutas (id_ruta, id_sede_origen, id_sede_destino, distancia_km,
                           duracion_estimada_hrs, precio_base) VALUES (%s,%s,%s,%s,%s,%s)""", [
            (1, 1, 3, 305, 8.0, 40), (2, 3, 1, 305, 8.0, 40), (3, 1, 4, 300, 7.5, 40), (4, 4, 1, 300, 7.5, 40),
            (7, 1, 5, 105, 2.5, 15), (8, 5, 1, 105, 2.5, 15), (9, 1, 6, 250, 5.5, 35), (10, 6, 1, 250, 5.5, 35),
            (11, 1, 7, 135, 3.0, 20), (12, 7, 1, 135, 3.0, 20)])
        print("   rutas creadas")
    if vacia("horarios"):
        cur.executemany("""INSERT INTO horarios (id_ruta, id_vehiculo_default, id_conductor_default, dia_semana,
                           hora_salida, precio_pasaje_base, precio_kg_carga_base) VALUES (%s,%s,%s,%s,%s,%s,%s)""", [
            (1, 1, 1, 'Jueves', '20:00', 40, 3.5), (1, 1, 1, 'Viernes', '20:00', 40, 3.5),
            (1, 3, 3, 'Sabado', '20:00', 40, 3.5), (2, 1, 1, 'Domingo', '22:00', 40, 3.5),
            (2, 3, 3, 'Lunes', '22:00', 40, 3.5), (3, 2, 2, 'Viernes', '21:00', 40, 3.5),
            (3, 2, 2, 'Sabado', '21:00', 40, 3.5), (4, 2, 2, 'Domingo', '20:00', 40, 3.5),
            (4, 10, 3, 'Lunes', '20:00', 40, 3.5),
            (7, 4, 4, 'Lunes', '06:30', 15, 2), (7, 9, 5, 'Miercoles', '06:30', 15, 2),
            (7, 4, 4, 'Viernes', '06:30', 15, 2), (8, 4, 4, 'Lunes', '14:00', 15, 2),
            (8, 9, 5, 'Miercoles', '14:00', 15, 2), (8, 4, 4, 'Viernes', '14:00', 15, 2),
            (9, 5, 6, 'Martes', '07:00', 35, 3), (9, 5, 6, 'Viernes', '07:00', 35, 3),
            (10, 6, 7, 'Jueves', '13:00', 35, 3), (10, 6, 7, 'Domingo', '13:00', 35, 3),
            (11, 7, 8, 'Lunes', '08:00', 20, 2.5), (11, 8, 9, 'Jueves', '08:00', 20, 2.5),
            (11, 7, 8, 'Sabado', '08:00', 20, 2.5), (12, 7, 8, 'Lunes', '15:00', 20, 2.5),
            (12, 8, 9, 'Jueves', '15:00', 20, 2.5), (12, 7, 8, 'Sabado', '15:00', 20, 2.5)])
        print("   horarios creados (25)")


# =====================================================================
# Utilidades
# =====================================================================
def sin_tildes(t):
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()


def crear_cliente(clientes, dnis, momento):
    while True:
        dni = str(random.randint(10000000, 79999999))
        if dni not in dnis:
            break
    dnis.add(dni)
    sexo = "M" if random.random() < 0.52 else "F"
    nombre = random.choice(NOMBRES_M if sexo == "M" else NOMBRES_F)
    nac = None
    if random.random() > PROB_SIN_FECHA_NAC:
        nac = momento.date() - timedelta(days=int(random.triangular(18, 75, 27)) * 365 + random.randint(0, 364))
    email = f"{sin_tildes(nombre).lower()}{random.randint(1, 999)}@gmail.com" if random.random() < 0.25 else None
    cid = len(clientes) + 1
    clientes[cid] = {"id": cid, "dni": dni, "nombres": f"{nombre} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}",
                     "nac": nac, "sexo": sexo, "tel": "9" + str(random.randint(10000000, 99999999)),
                     "email": email, "creado": momento}
    return cid


def elegir_cliente(clientes, pool, dnis, en_viaje, momento):
    elegido = None
    if pool and random.random() > PROB_CLIENTE_NUEVO:
        for _ in range(5):
            c = random.choice(pool)
            if c not in en_viaje:
                elegido = c
                break
    if elegido is None:
        elegido = crear_cliente(clientes, dnis, momento)
    en_viaje.add(elegido)
    pool.append(elegido)
    if momento < clientes[elegido]["creado"]:
        clientes[elegido]["creado"] = momento
    return elegido


def momento_venta(salida, anticipado):
    dias_antes = min(14, int(random.expovariate(1 / (4.0 if anticipado else 2.5))))
    if dias_antes == 0:
        return salida - timedelta(minutes=random.randint(20, 360))
    return datetime.combine(salida.date() - timedelta(days=dias_antes), time(random.randint(7, 21), random.randint(0, 59)))


def medio(x):
    return round(x * 2) / 2


def libre(lista, salida):
    libres = [x for x in lista if x["libre_desde"] <= salida]
    return min(libres, key=lambda x: x["libre_desde"]) if libres else None


# =====================================================================
# Catálogos
# =====================================================================
def cargar_catalogos(cur, desde):
    cur.execute("SELECT id_sede, ciudad FROM sedes")
    ciudad = {f["id_sede"]: f["ciudad"] for f in cur.fetchall()}
    cur.execute("SELECT id_usuario FROM usuarios WHERE id_rol = 4 AND estado = 'Activo' LIMIT 1")
    f = cur.fetchone()
    boletero = f["id_usuario"] if f else None

    antes = datetime.combine(desde, time.min) - timedelta(days=1)
    cur.execute("SELECT id_vehiculo, tipo, capacidad_asientos, capacidad_carga_kg FROM vehiculo")
    vehiculos = {}
    for f in cur.fetchall():
        km = random.randint(60000, 250000)
        vehiculos[f["id_vehiculo"]] = {"id": f["id_vehiculo"], "asientos": f["capacidad_asientos"],
                                       "carga_kg": float(f["capacidad_carga_kg"]), "libre_desde": antes,
                                       "km": km, "km_prev": km - random.randint(0, 9000)}
    pools = {c: [vehiculos[i] for i in ids if i in vehiculos] for c, ids in FLOTA_CORREDOR.items()}
    cur.execute("SELECT id_conductor FROM conductor WHERE estado = 'Activo'")
    conductores = [{"id": f["id_conductor"], "libre_desde": antes} for f in cur.fetchall()]

    cur.execute("""SELECT h.id_horario, h.dia_semana, h.hora_salida, h.precio_pasaje_base, h.precio_kg_carga_base,
                          h.id_vehiculo_default, h.id_conductor_default,
                          r.id_sede_origen, r.id_sede_destino, r.distancia_km, r.duracion_estimada_hrs
                   FROM horarios h JOIN rutas r ON r.id_ruta = h.id_ruta
                   WHERE h.estado = 'Activo' AND r.activa = 1""")
    horarios = []
    for f in cur.fetchall():
        sale = f["id_sede_origen"] == ID_SEDE_PASCO
        otra = ciudad[f["id_sede_destino"] if sale else f["id_sede_origen"]]
        if otra not in pools:
            print(f"   (se omite horario {f['id_horario']}: corredor '{otra}' sin flota)")
            continue
        horarios.append({"id": f["id_horario"], "dia": DIAS[f["dia_semana"]], "hora": f["hora_salida"],
                         "precio": float(f["precio_pasaje_base"]), "precio_kg": float(f["precio_kg_carga_base"]),
                         "dist": float(f["distancia_km"]), "dur": int(float(f["duracion_estimada_hrs"]) * 60),
                         "origen": f["id_sede_origen"], "corredor": otra, "sale_pasco": sale,
                         "veh_def": f["id_vehiculo_default"], "cond_def": f["id_conductor_default"]})
    return horarios, pools, vehiculos, conductores, boletero


# =====================================================================
# Simulación
# =====================================================================
def simular(horarios, pools, conductores, boletero, desde, hasta, ahora):
    clientes, pool, dnis = {}, [], set()
    viajes, reservas, pasajes, encomiendas, incidentes, mantenimientos = [], [], [], [], [], []
    c_viaje, c_res, c_pas, c_enc, c_inc, c_mant = (itertools.count(1) for _ in range(6))
    st = {"cancelados": 0, "sin_flota": 0, "realizados": 0, "alta": 0, "futuros": 0}

    def nueva_reserva(cid, momento, monto, estado, sede, canal):
        idr = next(c_res)
        if canal == "terminal":
            metodo, usuario, sede_v = random.choices(METODOS_TERM, PESOS_TERM)[0], boletero, sede
        else:
            metodo, usuario, sede_v = random.choices(METODOS_DIG, PESOS_DIG)[0], None, None
        reservas.append((idr, cid, usuario, sede_v, momento, monto, metodo, canal,
                         random.choices(["boleta", "ticket"], [92, 8])[0], estado))
        return idr

    plan, dia = [], desde
    while dia <= hasta + timedelta(days=DIAS_FUTUROS):
        for h in horarios:
            if dia.weekday() == h["dia"]:
                plan.append((datetime.combine(dia, time.min) + h["hora"], h))
        dia += timedelta(days=1)
    plan.sort(key=lambda x: (x[0], x[1]["id"]))

    for salida, h in plan:
        fecha = salida.date()
        es_fer = es_feriado_peru(fecha)
        es_vis = es_feriado_peru(fecha + timedelta(days=1))
        pico = es_fer or es_vis
        corredor = h["corredor"]
        llegada_prog = salida + timedelta(minutes=h["dur"])
        precio_viaje = medio(h["precio"] * (1.10 if pico else 1.0))

        # --- Viajes futuros: solo programados, con vehículo y conductor por defecto ---
        if fecha > hasta:
            idv = next(c_viaje)
            viajes.append((idv, h["id"], h["veh_def"], h["cond_def"], fecha, salida, None, llegada_prog,
                           None, precio_viaje, "Programado", int(es_fer)))
            st["futuros"] += 1
            continue

        vehiculo = libre(pools[corredor], salida)
        conductor = libre(conductores, salida) if vehiculo else None
        sin_flota = vehiculo is None or conductor is None
        cancelado = sin_flota or random.random() < PROB_CANCELACION

        salida_real = llegada_real = None
        incidencia, grave = None, False
        if not cancelado:
            escala = max(0.3, h["dur"] / 480)
            retraso_salida = max(0, round(random.gauss(5, 6)))
            retraso_ruta = max(0, round(random.gauss(10 * escala, 6 * escala)))
            minutos_inc = 0
            if random.random() < PROB_INCIDENCIA:
                tipo = random.choices(TIPOS_INC, PESOS_INC)[0]
                minutos_inc = max(15, round(random.randint(30, 180) * max(escala, 0.4)))
                grave = tipo == "falla_mecanica" and random.random() < PROB_CORRECTIVO_TRAS_FALLA
                incidencia = (tipo, minutos_inc, salida + timedelta(
                    minutes=retraso_salida + random.randint(10, max(11, h["dur"] - 10))))
            salida_real = salida + timedelta(minutes=retraso_salida)
            llegada_real = llegada_prog + timedelta(minutes=retraso_salida + retraso_ruta + minutos_inc)
            if llegada_real > ahora:
                continue

        idv = next(c_viaje)

        if vehiculo is not None:
            asientos = vehiculo["asientos"]
            demanda = (OCUPACION_BASE[corredor] * FACTOR_DIA[fecha.weekday()] * FACTOR_MES[fecha.month]
                       * (FACTOR_SENTIDO_LIMA if corredor == "Lima" and (
                           (h["sale_pasco"] and fecha.weekday() in (4, 5)) or
                           (not h["sale_pasco"] and fecha.weekday() in (6, 0))) else 1.0)
                       * (FACTOR_FERIADO if es_fer else 1.0) * (FACTOR_VISPERA if es_vis else 1.0)
                       * random.gauss(1, RUIDO_DEMANDA))
            vendidos = round(asientos * min(1.0, max(0.05, demanda)))
            if not cancelado:
                st["realizados"] += 1
                if vendidos / asientos >= UMBRAL_ALTA:
                    st["alta"] += 1
            en_viaje = set()
            for nro in random.sample(range(1, asientos + 1), vendidos):
                momento = momento_venta(salida, pico)
                cid = elegir_cliente(clientes, pool, dnis, en_viaje, momento)
                c = clientes[cid]
                precio = medio(precio_viaje * (0.85 if random.random() < PROB_DESCUENTO else 1))
                if cancelado:
                    est_p, est_r = "anulado", "anulada"
                elif random.random() < PROB_NO_SHOW:
                    est_p, est_r = "no_show", "pagada"
                else:
                    est_p, est_r = "abordado", "pagada"
                idr = nueva_reserva(cid, momento, precio, est_r, h["origen"], random.choices(CANALES, PESOS_CANAL)[0])
                pasajes.append((next(c_pas), idr, idv, nro, c["dni"], c["nombres"], c["nac"], c["sexo"], precio, est_p))
            if not cancelado:
                for _ in range(round(vendidos * PROB_ANULADO)):
                    momento = momento_venta(salida, pico)
                    cid = elegir_cliente(clientes, pool, dnis, set(), momento)
                    c = clientes[cid]
                    idr = nueva_reserva(cid, momento, precio_viaje, "anulada", h["origen"],
                                        random.choices(CANALES, PESOS_CANAL)[0])
                    pasajes.append((next(c_pas), idr, idv, random.randint(1, asientos), c["dni"], c["nombres"],
                                    c["nac"], c["sexo"], precio_viaje, "anulado"))

        if cancelado:
            st["sin_flota" if sin_flota else "cancelados"] += 1
            viajes.append((idv, h["id"], vehiculo["id"] if vehiculo else None, conductor["id"] if conductor else None,
                           fecha, salida, None, llegada_prog, None, precio_viaje, "Cancelado", int(es_fer)))
            continue

        carga = 0.0
        for _ in range(max(0, round(random.gauss(MEDIA_ENCOMIENDAS[corredor], 1.2)))):
            peso = round(max(0.5, min(120, random.lognormvariate(2.0, 0.9))), 2)
            if carga + peso > vehiculo["carga_kg"]:
                break
            carga += peso
            momento = salida - timedelta(hours=random.randint(1, 24))
            cid = elegir_cliente(clientes, pool, dnis, set(), momento)
            precio = round(max(5.0, peso * h["precio_kg"]), 1)
            idr = nueva_reserva(cid, momento, precio, "pagada", h["origen"], "terminal")
            entregada = llegada_real + timedelta(hours=random.randint(1, 48))
            if random.random() < 0.003:
                estado, entregada = "Perdido", None
            elif entregada > ahora:
                estado, entregada = "En transito", None
            else:
                estado = "Entregado"
            encomiendas.append((next(c_enc), idr, idv, str(random.randint(10000000, 79999999)),
                                f"{random.choice(NOMBRES_M + NOMBRES_F)} {random.choice(APELLIDOS)}",
                                "9" + str(random.randint(10000000, 99999999)), random.choice(DESC_ENC), peso,
                                str(random.randint(100000, 999999)), estado, precio, entregada))

        if incidencia:
            tipo, minutos, momento = incidencia
            incidentes.append((next(c_inc), idv, tipo, DESC_INC[tipo], random.choice(LUGARES[corredor]),
                               momento, minutos))

        vehiculo["km"] += round(h["dist"])
        vehiculo["libre_desde"] = llegada_real + timedelta(minutes=45)
        conductor["libre_desde"] = llegada_real + timedelta(hours=8 if h["dur"] >= 300 else 1)

        if grave:
            dias = random.randint(2, 6)
            mantenimientos.append((next(c_mant), vehiculo["id"], "correctivo", random.choice(DESC_CORR),
                                   llegada_real.date(), vehiculo["km"], round(random.uniform(800, 6000), 2), dias))
            vehiculo["libre_desde"] = llegada_real + timedelta(days=dias)
        elif vehiculo["km"] - vehiculo["km_prev"] >= KM_PREVENTIVO:
            dias = random.randint(1, 2)
            mantenimientos.append((next(c_mant), vehiculo["id"], "preventivo", random.choice(DESC_PREV),
                                   llegada_real.date(), vehiculo["km"], round(random.uniform(350, 1200), 2), dias))
            vehiculo["km_prev"] = vehiculo["km"]
            vehiculo["libre_desde"] = llegada_real + timedelta(days=dias)

        viajes.append((idv, h["id"], vehiculo["id"], conductor["id"], fecha, salida, salida_real, llegada_prog,
                       llegada_real, precio_viaje, "Finalizado", int(es_fer)))

    return dict(clientes=clientes, viajes=viajes, reservas=reservas, pasajes=pasajes, encomiendas=encomiendas,
                incidentes=incidentes, mantenimientos=mantenimientos, stats=st)


# =====================================================================
# Guardado
# =====================================================================
def insertar(cur, tabla, columnas, filas, lote=2000):
    sql = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({', '.join(['%s'] * len(columnas))})"
    for i in range(0, len(filas), lote):
        cur.executemany(sql, filas[i:i + lote])
    print(f"   {tabla:<22}{len(filas):>9,} filas")


def guardar(cur, d, vehiculos, ahora):
    for t in ("incidentes_ruta", "mantenimientos", "detalle_encomiendas", "detalle_pasajes",
              "reservas_ventas", "programacion_viaje", "clientes"):
        cur.execute(f"DELETE FROM {t}")
    print("Guardando:")
    insertar(cur, "clientes", ["id_cliente", "tipo_doc", "num_documento", "nombres_razon_social",
                               "fecha_nacimiento", "sexo", "telefono", "email", "creado_en"],
             [(c["id"], "DNI", c["dni"], c["nombres"], c["nac"], c["sexo"], c["tel"], c["email"], c["creado"])
              for c in sorted(d["clientes"].values(), key=lambda c: c["id"])])
    insertar(cur, "programacion_viaje",
             ["id_viaje", "id_horario", "id_vehiculo", "id_conductor", "fecha_salida", "salida_programada",
              "salida_real", "llegada_programada", "llegada_real", "precio_pasaje", "estado_viaje", "es_feriado"],
             d["viajes"])
    insertar(cur, "reservas_ventas", ["id_reserva", "id_cliente", "id_usuario", "id_sede", "fecha_emision",
                                      "monto_total", "metodo_pago", "canal_venta", "tipo_comprobante", "estado"],
             d["reservas"])
    insertar(cur, "detalle_pasajes", ["id_detalle_pasaje", "id_reserva", "id_viaje", "numero_asiento",
                                      "dni_pasajero", "nombre_pasajero", "fecha_nacimiento", "sexo",
                                      "precio_pagado", "estado"], d["pasajes"])
    insertar(cur, "detalle_encomiendas", ["id_detalle_encomienda", "id_reserva", "id_viaje", "dni_destinatario",
                                          "nombre_destinatario", "telefono_destinatario", "descripcion_contenido",
                                          "peso_kg", "clave_recojo", "estado_entrega", "precio_pagado",
                                          "entregado_en"], d["encomiendas"])
    insertar(cur, "incidentes_ruta", ["id_incidente", "id_viaje", "tipo_incidente", "descripcion",
                                      "lugar_referencial", "fecha_hora", "minutos_retraso_estimado"],
             d["incidentes"])
    insertar(cur, "mantenimientos", ["id_mantenimiento", "id_vehiculo", "tipo", "descripcion", "fecha",
                                     "km_al_momento", "costo", "dias_inoperativo"], d["mantenimientos"])
    cur.executemany("UPDATE vehiculo SET kilometraje_actual = %s, estado = %s WHERE id_vehiculo = %s",
                    [(v["km"], "Mantenimiento" if v["libre_desde"] > ahora else "Disponible", v["id"])
                     for v in vehiculos.values()])


def main():
    if input("Esto BORRA viajes, ventas, clientes, encomiendas, incidentes y mantenimientos de la base "
             "indicada en el .env y genera datos nuevos.\n(Detén Flask.) Escribe SI para continuar: "
             ).strip().upper() != "SI":
        print("Cancelado.")
        return
    random.seed(SEMILLA)
    ahora = datetime.now()
    hoy = ahora.date()
    desde, hasta = hoy - timedelta(days=DIAS_HISTORIA), hoy - timedelta(days=1)

    conn = conectar()
    try:
        with conn.cursor() as cur:
            print(f"Base: {os.getenv('DB_HOST', 'localhost')} / {os.getenv('DB_NAME', 'agencia_transportes')}")
            sembrar_base(cur)
            horarios, pools, vehiculos, conductores, boletero = cargar_catalogos(cur, desde)
            print(f"Simulando {desde} a {hasta}: {len(horarios)} horarios, {len(vehiculos)} vehículos, "
                  f"{len(conductores)} conductores...")
            datos = simular(horarios, pools, conductores, boletero, desde, hasta, ahora)
            guardar(cur, datos, vehiculos, ahora)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    s = datos["stats"]
    print(f"\nListo. Cancelados: {s['cancelados']} (sin flota: {s['sin_flota']}). "
          f"Viajes programados a futuro: {s['futuros']}.")
    print(f"Alta ocupación (>= {UMBRAL_ALTA:.0%}): {100 * s['alta'] / max(1, s['realizados']):.1f}% (ideal 30-50%).")


if __name__ == "__main__":
    main()