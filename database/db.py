import os
import mysql.connector
from mysql.connector import pooling

# Cargar credenciales desde Variables de Entorno (Render/Producción)
# Si no existen, usa los valores locales por defecto
DB_HOST = os.environ.get('MYSQLHOST', 'localhost')
DB_USER = os.environ.get('MYSQLUSER', 'root')
DB_PASSWORD = os.environ.get('MYSQLPASSWORD', '')
DB_NAME = os.environ.get('MYSQLDATABASE', 'transportes_carhuamayo')
DB_PORT = int(os.environ.get('MYSQLPORT', 3306))

try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT
    )
    print("✅ Conexión con la Base de Datos establecida correctamente.")
except mysql.connector.Error as err:
    print(f"❌ Error al conectar con la base de datos MySQL: {err}")
    db_pool = None

def get_connection():
    if db_pool:
        return db_pool.get_connection()
    raise Exception("El Pool de conexiones a MySQL no está inicializado.")