from flask import Flask, render_template, request, redirect, url_for, session
from config import Config
from models import db
import os

# Importar Blueprints
from routes.admin.vehiculos import vehiculos_bp
from routes.admin.conductores import conductores_bp
from routes.admin.sedes import sedes_bp
from routes.admin.rutas import rutas_bp
from routes.auth.routes import auth_bp
from routes.admin.dashboard import admin_bp
from routes.admin.viajes import admin_viajes_bp
from routes.public.main import public_bp
from routes.public.reservas import reservas_bp
from routes.admin.incidentes import incidentes_bp
from routes.public.mapa import mapa_bp
from routes.admin.mapa import mapa_admin_bp
from routes.admin.predicciones import predicciones_bp
from routes.public.encomiendas import encomiendas_bp
from routes.admin.encomiendas import encomiendas_admin_bp
from routes.admin.mantenimientos import mantenimientos_bp
from routes.admin.combustible import combustible_bp
from routes.admin.programacion import programacion_bp

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar SQLAlchemy con la aplicación Flask
db.init_app(app)

app.secret_key = app.config.get('SECRET_KEY', 'clave_secreta_desarrollo_pasco_2026')

# Registrar Blueprints
app.register_blueprint(vehiculos_bp)
app.register_blueprint(conductores_bp)
app.register_blueprint(sedes_bp)
app.register_blueprint(rutas_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(admin_viajes_bp)
app.register_blueprint(public_bp)
app.register_blueprint(reservas_bp)
app.register_blueprint(incidentes_bp)
app.register_blueprint(mapa_bp)
app.register_blueprint(mapa_admin_bp)
app.register_blueprint(predicciones_bp)
app.register_blueprint(encomiendas_bp)
app.register_blueprint(encomiendas_admin_bp)
app.register_blueprint(mantenimientos_bp)
app.register_blueprint(combustible_bp)
app.register_blueprint(programacion_bp)

# Proteger rutas administrativas
@app.before_request
def restringir_acceso_admin():
    if request.path.startswith('/admin') and 'user_id' not in session:
        return redirect(url_for('auth.login'))

@app.route('/')
def home():
    return render_template('public/index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)