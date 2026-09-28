import mysql.connector
from mysql.connector import pooling
from config import Config

try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        port=Config.DB_PORT
    )
except mysql.connector.Error as err:
    print(f"Error al conectar con la base de datos MySQL: {err}")
    db_pool = None

def get_connection():
    if db_pool:
        return db_pool.get_connection()
    raise Exception("El Pool de conexiones a MySQL no está inicializado.")