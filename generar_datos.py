# generar_datos.py
import random
from datetime import datetime, timedelta
from database.db import get_connection

def poblar_historico():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    print("--- 1. Generando Clientes Base ---")
    nombres_sample = ["Juan", "María", "Carlos", "Ana", "Luis", "Rosa", "Pedro", "Elena", "Lucía", "Jorge", "Valeria", "Diego", "Camila", "Andrés", "Sofía", "Pool", "Erick", "Nayeli", "Jennifer", "Isabel", "Gabriel", "Yanet", "Jean", "Jesus", "Aracelly"]
    apellidos_sample = ["Quispe", "Rojas", "García", "López", "Flores", "Espinoza", "Torres", "Mendoza", "Cárdenas", "Pérez", "Salazar", "Chávez", "Huamán", "Sánchez", "Rivera", "Catillo", "Rosas", "Parra", "Lopez", "Espinoza", "De la Cruz", "Condor", "Berrospi", "Condezo", "Pinto"]
    
    clientes_ids = []
    for i in range(150):
        dni = str(40000000 + i)
        nombre = f"{random.choice(nombres_sample)} {random.choice(apellidos_sample)}"
        tel = f"98{random.randint(1000007, 9999999)}"
        email = f"cliente{i}@gmail.com"
        
        try:
            cursor.execute("""
                INSERT INTO clientes (num_documento, nombres_razon_social, telefono, email)
                VALUES (%s, %s, %s, %s)
            """, (dni, nombre, tel, email))
            clientes_ids.append(cursor.lastrowid)
        except Exception:
            pass # Ignorar duplicados si re-ejecutas

    conn.commit()

    # Si ya existían clientes en la BD:
    cursor.execute("SELECT id_cliente FROM clientes")
    clientes_ids = [r['id_cliente'] for r in cursor.fetchall()]

    print("--- 2. Obteniendo Horarios Existentes ---")
    cursor.execute("""
        SELECT h.id_horario, h.id_ruta, h.dia_semana, h.hora_salida, h.precio_pasaje_base, v.capacidad_asientos
        FROM horarios h
        JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
        WHERE h.estado = 'Activo'
    """)
    horarios = cursor.fetchall()

    dias_map = {
        'Lunes': 0, 'Martes': 1, 'Miercoles': 2, 'Jueves': 3,
        'Viernes': 4, 'Sabado': 5, 'Domingo': 6
    }

    # Generar viajes desde Hace 8 Meses hasta Hoy
    fecha_inicio = datetime(2026, 1, 1).date()
    fecha_fin = datetime(2026, 9, 27).date()

    print(f"--- 3. Generando Viajes y Ventas ({fecha_inicio} a {fecha_fin}) ---")
    
    dia_actual = fecha_inicio
    total_viajes = 0
    total_pasajes = 0

    while dia_actual <= fecha_fin:
        num_dia_semana = dia_actual.weekday() # 0 = Lunes, 6 = Domingo

        for h in horarios:
            if dias_map[h['dia_semana']] == num_dia_semana:
                # Insertar Viaje Programado
                try:
                    cursor.execute("""
                        INSERT INTO programacion_viaje (id_horario, fecha_salida, estado_viaje)
                        VALUES (%s, %s, 'Finalizado')
                    """, (h['id_horario'], dia_actual))
                    id_viaje = cursor.lastrowid
                    total_viajes += 1
                except Exception:
                    continue # Viaje ya programado previamente

                # Determinar % de ocupación según el día
                capacidad = h['capacidad_asientos']
                if num_dia_semana in [4, 5, 6]: # Viernes a Domingo -> Alta Ocupación
                    porcentaje = random.uniform(0.75, 1.00)
                else: # Lunes a Jueves -> Ocupación Media
                    porcentaje = random.uniform(0.35, 0.70)

                asientos_a_vender = int(capacidad * porcentaje)
                asientos_libres = list(range(1, capacidad + 1))
                random.shuffle(asientos_libres)

                # Generar Pasajes Vendidos para este viaje
                for k in range(asientos_a_vender):
                    cliente_id = random.choice(clientes_ids)
                    num_asiento = asientos_libres.pop()
                    
                    # Pequeña variación de precio (+/- 10%)
                    factor_precio = random.choice([0.9, 1.0, 1.0, 1.1])
                    precio_final = round(float(h['precio_pasaje_base']) * factor_precio, 2)

                    # 1. Reserva Cabecera
                    cursor.execute("""
                        INSERT INTO reservas_ventas (id_cliente, fecha_emision, monto_total, metodo_pago, tipo_comprobante)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        cliente_id, 
                        datetime.combine(dia_actual, datetime.min.time()) + timedelta(hours=random.randint(1, 10)),
                        precio_final, 
                        random.choice(['Efectivo', 'Yape', 'Tarjeta']), 
                        'Boleta'
                    ))
                    id_reserva = cursor.lastrowid

                    # 2. Detalle Pasaje
                    cursor.execute("""
                        INSERT INTO detalle_pasajes (id_reserva, id_viaje, numero_asiento, dni_pasajero, nombre_pasajero, precio_pagado)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        id_reserva, id_viaje, num_asiento, 
                        str(random.randint(10000000, 79999999)), 
                        "Pasajero Generado", precio_final
                    ))
                    total_pasajes += 1

        dia_actual += timedelta(days=1)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ ¡Poblado exitoso! Se crearon {total_viajes} viajes y {total_pasajes} pasajes vendidos.")

if __name__ == "__main__":
    poblar_historico()