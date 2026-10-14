import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key_123')
    
    # Configuración de MySQL
    DB_HOST = os.getenv('DB_HOST', os.getenv('MYSQLHOST', 'localhost'))
    DB_USER = os.getenv('DB_USER', os.getenv('MYSQLUSER', 'root'))
    DB_PASSWORD = os.getenv('DB_PASSWORD', os.getenv('MYSQLPASSWORD', ''))
    DB_NAME = os.getenv('DB_NAME', os.getenv('MYSQLDATABASE', 'agencia_transportes'))
    DB_PORT = int(os.getenv('DB_PORT', os.getenv('MYSQLPORT', 3306)))
    
    # Configuración requerida por Flask-SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APISPERU_TOKEN = os.getenv('APISPERU_TOKEN', '')
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

    DB_SSL_CA = os.getenv('DB_SSL_CA', '')
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,      # reconecta si Aiven apagó la conexión
        "pool_recycle": 280,
        **({"connect_args": {"ssl": {"ca": DB_SSL_CA}}} if DB_SSL_CA else {}),
    }