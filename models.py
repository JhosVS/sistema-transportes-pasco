from database.db import get_connection
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash


# ============================================================
# MODELO: VEHÍCULO
# ============================================================
class VehiculoModel:
    @staticmethod
    def get_todos():
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT *
            FROM vehiculo
            ORDER BY id_vehiculo DESC
        """
        cursor.execute(sql)
        vehiculos = cursor.fetchall()
        cursor.close()
        conn.close()
        return vehiculos

    @staticmethod
    def get_by_id(id_vehiculo):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT *
            FROM vehiculo
            WHERE id_vehiculo = %s
        """
        cursor.execute(sql, (id_vehiculo,))
        vehiculo = cursor.fetchone()
        cursor.close()
        conn.close()
        return vehiculo

    @staticmethod
    def crear(placa, marca, modelo, color, capacidad_asientos, capacidad_carga_kg, estado):
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO vehiculo
            (placa, marca, modelo, color, capacidad_asientos, capacidad_carga_kg, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            placa,
            marca,
            modelo,
            color,
            capacidad_asientos,
            capacidad_carga_kg,
            estado
        )
        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def actualizar(id_vehiculo, placa, marca, modelo, color, capacidad_asientos, capacidad_carga_kg, estado):
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE vehiculo
            SET placa=%s,
                marca=%s,
                modelo=%s,
                color=%s,
                capacidad_asientos=%s,
                capacidad_carga_kg=%s,
                estado=%s
            WHERE id_vehiculo=%s
        """
        valores = (
            placa,
            marca,
            modelo,
            color,
            capacidad_asientos,
            capacidad_carga_kg,
            estado,
            id_vehiculo
        )
        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def eliminar(id_vehiculo):
        """
        Eliminación lógica:
        No se elimina el registro de la base de datos.
        Simplemente cambia su estado a Inactivo.
        """
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE vehiculo
            SET estado = 'Inactivo'
            WHERE id_vehiculo = %s
        """
        cursor.execute(sql, (id_vehiculo,))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def activar(id_vehiculo):
        conn = get_connection()
        cursor = conn.cursor()

        sql = """
            UPDATE vehiculo
            SET estado = 'Disponible'
            WHERE id_vehiculo = %s
        """

        cursor.execute(sql, (id_vehiculo,))
        conn.commit()

        cursor.close()
        conn.close()


# ============================================================
# MODELO: CONDUCTOR
# ============================================================
class ConductorModel:
    @staticmethod
    def get_todos():
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT *
            FROM conductor
            ORDER BY id_conductor DESC
        """
        cursor.execute(sql)
        conductores = cursor.fetchall()
        cursor.close()
        conn.close()
        return conductores

    @staticmethod
    def get_by_id(id_conductor):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT *
            FROM conductor
            WHERE id_conductor = %s
        """
        cursor.execute(sql, (id_conductor,))
        conductor = cursor.fetchone()
        cursor.close()
        conn.close()
        return conductor

    @staticmethod
    def crear(dni, nombres, apellidos, telefono, licencia_conducir, estado):
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO conductor
            (dni, nombres, apellidos, telefono, licencia_conducir, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        valores = (
            dni,
            nombres,
            apellidos,
            telefono,
            licencia_conducir,
            estado
        )
        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def actualizar(id_conductor, dni, nombres, apellidos, telefono, licencia_conducir, estado):
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE conductor
            SET dni=%s,
                nombres=%s,
                apellidos=%s,
                telefono=%s,
                licencia_conducir=%s,
                estado=%s
            WHERE id_conductor=%s
        """
        valores = (
            dni,
            nombres,
            apellidos,
            telefono,
            licencia_conducir,
            estado,
            id_conductor
        )
        cursor.execute(sql, valores)
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def eliminar(id_conductor):
        """
        Eliminación lógica:
        No se elimina el registro de la base de datos.
        Simplemente cambia su estado a Inactivo.
        """
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE conductor
            SET estado = 'Inactivo'
            WHERE id_conductor = %s
        """
        cursor.execute(sql, (id_conductor,))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def activar(id_conductor):
        conn = get_connection()
        cursor = conn.cursor()
        sql = """
            UPDATE conductor
            SET estado = 'Activo'
            WHERE id_conductor = %s
        """
        cursor.execute(sql, (id_conductor,))
        conn.commit()
        cursor.close()
        conn.close()

# ============================================================
# MODELO: SEDE
# ============================================================
class SedeModel:

    @staticmethod
    def get_todas():
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sedes ORDER BY id_sede DESC")
        sedes = cursor.fetchall()
        cursor.close()
        conn.close()
        return sedes

    @staticmethod
    def get_by_id(id_sede):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM sedes WHERE id_sede = %s"
        cursor.execute(sql, (id_sede,))
        sede = cursor.fetchone()
        cursor.close()
        conn.close()
        return sede

    @staticmethod
    def crear(nombre_sede, direccion, latitud, longitud):
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO sedes (nombre_sede, direccion, latitud, longitud) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre_sede, direccion, latitud or None, longitud or None))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def actualizar(id_sede, nombre_sede, direccion, latitud, longitud):
        conn = get_connection()
        cursor = conn.cursor()
        sql = "UPDATE sedes SET nombre_sede=%s, direccion=%s, latitud=%s, longitud=%s WHERE id_sede=%s"
        cursor.execute(sql, (nombre_sede, direccion, latitud or None, longitud or None, id_sede))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def eliminar(id_sede):
        conn = get_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM sedes WHERE id_sede = %s"
        cursor.execute(sql, (id_sede,))
        conn.commit()
        cursor.close()
        conn.close()


# ============================================================
# MODELO: RUTA
# ============================================================
class RutaModel:

    @staticmethod
    def get_todas():
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT r.*, 
                   so.nombre_sede AS origen_nombre, 
                   sd.nombre_sede AS destino_nombre
            FROM rutas r
            INNER JOIN sedes so ON r.id_sede_origen = so.id_sede
            INNER JOIN sedes sd ON r.id_sede_destino = sd.id_sede
            ORDER BY r.id_ruta DESC
        """
        cursor.execute(sql)
        rutas = cursor.fetchall()
        cursor.close()
        conn.close()
        return rutas

    @staticmethod
    def get_by_id(id_ruta):
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM rutas WHERE id_ruta = %s"
        cursor.execute(sql, (id_ruta,))
        ruta = cursor.fetchone()
        cursor.close()
        conn.close()
        return ruta

    @staticmethod
    def crear(id_sede_origen, id_sede_destino, duracion_estimada_hrs):
        conn = get_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO rutas (id_sede_origen, id_sede_destino, duracion_estimada_hrs) VALUES (%s, %s, %s)"
        cursor.execute(sql, (id_sede_origen, id_sede_destino, duracion_estimada_hrs))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def actualizar(id_ruta, id_sede_origen, id_sede_destino, duracion_estimada_hrs):
        conn = get_connection()
        cursor = conn.cursor()
        sql = "UPDATE rutas SET id_sede_origen=%s, id_sede_destino=%s, duracion_estimada_hrs=%s WHERE id_ruta=%s"
        cursor.execute(sql, (id_sede_origen, id_sede_destino, duracion_estimada_hrs, id_ruta))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def eliminar(id_ruta):
        conn = get_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM rutas WHERE id_ruta = %s"
        cursor.execute(sql, (id_ruta,))
        conn.commit()
        cursor.close()
        conn.close()

# ============================================================
# MODELO: USUARIO
# ============================================================
class UsuarioModel:

    @staticmethod
    def get_by_email(email):
        """Obtiene un usuario por su correo electrónico junto con el nombre de su sede"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT u.*, s.nombre_sede 
            FROM usuarios u
            LEFT JOIN sedes s ON u.id_sede = s.id_sede
            WHERE u.email = %s LIMIT 1
        """
        cursor.execute(sql, (email,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()
        return usuario

    @staticmethod
    def verificar_password(hash_o_texto, password_ingresada):
        """
        Verifica la contraseña. Admite tanto hashes seguros de Werkzeug 
        como contraseñas en texto plano (para compatibilidad con el SQL inicial).
        """
        if hash_o_texto.startswith('pbkdf2:') or hash_o_texto.startswith('scrypt:'):
            return check_password_hash(hash_o_texto, password_ingresada)
        return hash_o_texto == password_ingresada

    @staticmethod
    def actualizar_password_hash(id_usuario, nueva_password):
        """Actualiza la contraseña del usuario a un hash seguro"""
        conn = get_connection()
        cursor = conn.cursor()
        hashed = generate_password_hash(nueva_password)
        sql = "UPDATE usuarios SET password = %s WHERE id_usuario = %s"
        cursor.execute(sql, (hashed, id_usuario))
        conn.commit()
        cursor.close()
        conn.close()