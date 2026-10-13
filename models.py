"""
models.py - Modelos Flask-SQLAlchemy que reflejan agencia_transportes (v3).

La estructura la define el script SQL; estos modelos solo la mapean.
NO uses db.create_all() contra esta base: ejecuta primero db_transportes.sql.

Requisitos:  pip install flask flask-sqlalchemy pymysql werkzeug bcrypt
Configuración en app.py:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://app_transportes:CambiaEstaClave_456@localhost/agencia_transportes"
        "?charset=utf8mb4"
    )
    db.init_app(app)
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import YEAR
from sqlalchemy.sql import func
import bcrypt
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


# =====================================================================
# 1. CATÁLOGOS
# =====================================================================
class Sede(db.Model):
    __tablename__ = "sedes"

    id_sede = db.Column(db.Integer, primary_key=True)
    nombre_sede = db.Column(db.String(100), nullable=False)
    ciudad = db.Column(db.String(60), nullable=False)
    departamento = db.Column(db.String(40), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    altitud_msnm = db.Column(db.Integer)
    latitud = db.Column(db.Numeric(10, 8))
    longitud = db.Column(db.Numeric(11, 8))
    activo = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Sede {self.id_sede} {self.nombre_sede}>"


class Vehiculo(db.Model):
    __tablename__ = "vehiculo"

    id_vehiculo = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10), nullable=False, unique=True)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    anio = db.Column(YEAR)
    color = db.Column(db.String(30))
    tipo = db.Column(db.Enum("bus", "minivan", "camion", name="vehiculo_tipo"),
                     nullable=False, default="bus")
    capacidad_asientos = db.Column(db.Integer, nullable=False)
    capacidad_carga_kg = db.Column(db.Numeric(8, 2), nullable=False)
    kilometraje_actual = db.Column(db.Integer, nullable=False, default=0)
    estado = db.Column(db.Enum("Disponible", "Mantenimiento", "Baja", name="vehiculo_estado"),
                       nullable=False, default="Disponible")

    def __repr__(self):
        return f"<Vehiculo {self.placa}>"


class Conductor(db.Model):
    __tablename__ = "conductor"

    id_conductor = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(8), nullable=False, unique=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(15), nullable=False)
    licencia_conducir = db.Column(db.String(20), nullable=False, unique=True)
    licencia_categoria = db.Column(db.String(10), nullable=False)
    licencia_vence = db.Column(db.Date, nullable=False)
    fecha_ingreso = db.Column(db.Date)
    estado = db.Column(db.Enum("Activo", "Inactivo", name="conductor_estado"),
                       nullable=False, default="Activo")

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"


class Cliente(db.Model):
    __tablename__ = "clientes"
    __table_args__ = (db.UniqueConstraint("tipo_doc", "num_documento"),)

    id_cliente = db.Column(db.Integer, primary_key=True)
    tipo_doc = db.Column(db.Enum("DNI", "RUC", "CE", "PASAPORTE", name="cliente_tipo_doc"),
                         nullable=False, default="DNI")
    num_documento = db.Column(db.String(15), nullable=False)
    nombres_razon_social = db.Column(db.String(150), nullable=False)
    fecha_nacimiento = db.Column(db.Date)
    sexo = db.Column(db.Enum("M", "F", "otro", name="cliente_sexo"))
    telefono = db.Column(db.String(15))
    email = db.Column(db.String(100))
    creado_en = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())


# =====================================================================
# 2. SEGURIDAD
# =====================================================================
class Rol(db.Model):
    __tablename__ = "roles"

    id_rol = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    nombre = db.Column(db.String(60), nullable=False)
    descripcion = db.Column(db.String(150))


class Usuario(db.Model):
    """Compatible con Flask-Login (is_authenticated, get_id, etc.)."""
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    id_rol = db.Column(db.Integer, db.ForeignKey("roles.id_rol"), nullable=False)
    id_sede = db.Column(db.Integer, db.ForeignKey("sedes.id_sede", ondelete="SET NULL"))
    id_conductor = db.Column(db.Integer,
                             db.ForeignKey("conductor.id_conductor", ondelete="SET NULL"),
                             unique=True)
    username = db.Column(db.String(40), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nombres = db.Column(db.String(80), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)
    estado = db.Column(db.Enum("Activo", "Inactivo", name="usuario_estado"),
                       nullable=False, default="Activo")
    debe_cambiar_clave = db.Column(db.Boolean, nullable=False, default=True)
    intentos_fallidos = db.Column(db.Integer, nullable=False, default=0)
    bloqueado_hasta = db.Column(db.DateTime)
    ultimo_login = db.Column(db.DateTime)
    creado_en = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    actualizado_en = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    rol = db.relationship("Rol")
    sede = db.relationship("Sede")
    conductor = db.relationship("Conductor")

    # --- contraseñas ---
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False

        # Soporte para hashes Bcrypt ($2a$, $2b$, $2y$)
        if self.password_hash.startswith(('$2a$', '$2b$', '$2y$')):
            try:
                return bcrypt.checkpw(
                    password.encode('utf-8'),
                    self.password_hash.encode('utf-8')
                )
            except Exception:
                return False

        # Soporte para hashes de Werkzeug (pbkdf2:, scrypt:)
        if self.password_hash.startswith(('pbkdf2:', 'scrypt:')):
            return check_password_hash(self.password_hash, password)

        # Soporte si estaba guardada en texto plano
        return self.password_hash == password

    # --- Flask-Login ---
    def get_id(self):
        return str(self.id_usuario)

    @property
    def is_active(self):
        return self.estado == "Activo"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def esta_bloqueado(self):
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > datetime.utcnow())


class AccesoLog(db.Model):
    __tablename__ = "accesos_log"

    id_acceso = db.Column(db.BigInteger, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"))
    username_intentado = db.Column(db.String(40), nullable=False)
    exitoso = db.Column(db.Boolean, nullable=False)
    motivo = db.Column(db.String(50))
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    fecha = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())


# =====================================================================
# 3. RUTAS, HORARIOS Y VIAJES
# =====================================================================
class Ruta(db.Model):
    __tablename__ = "rutas"
    __table_args__ = (
        db.UniqueConstraint("id_sede_origen", "id_sede_destino"),
        db.CheckConstraint("id_sede_origen <> id_sede_destino", name="chk_origen_destino_dif"),
    )

    id_ruta = db.Column(db.Integer, primary_key=True)
    id_sede_origen = db.Column(db.Integer, db.ForeignKey("sedes.id_sede"), nullable=False)
    id_sede_destino = db.Column(db.Integer, db.ForeignKey("sedes.id_sede"), nullable=False)
    distancia_km = db.Column(db.Numeric(7, 2), nullable=False)
    duracion_estimada_hrs = db.Column(db.Numeric(4, 2), nullable=False)
    precio_base = db.Column(db.Numeric(8, 2), nullable=False)
    activa = db.Column(db.Boolean, nullable=False, default=True)

    origen = db.relationship("Sede", foreign_keys=[id_sede_origen])
    destino = db.relationship("Sede", foreign_keys=[id_sede_destino])

    def __repr__(self):
        return f"<Ruta {self.id_ruta}: {self.id_sede_origen}->{self.id_sede_destino}>"


DIAS_SEMANA = ("Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo")


class Horario(db.Model):
    __tablename__ = "horarios"
    __table_args__ = (db.UniqueConstraint("id_ruta", "dia_semana", "hora_salida"),)

    id_horario = db.Column(db.Integer, primary_key=True)
    id_ruta = db.Column(db.Integer, db.ForeignKey("rutas.id_ruta"), nullable=False)
    id_vehiculo_default = db.Column(db.Integer, db.ForeignKey("vehiculo.id_vehiculo"))
    id_conductor_default = db.Column(db.Integer, db.ForeignKey("conductor.id_conductor"))
    dia_semana = db.Column(db.Enum(*DIAS_SEMANA, name="horario_dia"), nullable=False)
    hora_salida = db.Column(db.Time, nullable=False)
    precio_pasaje_base = db.Column(db.Numeric(8, 2), nullable=False)
    precio_kg_carga_base = db.Column(db.Numeric(8, 2), nullable=False)
    estado = db.Column(db.Enum("Activo", "Inactivo", name="horario_estado"),
                       nullable=False, default="Activo")

    ruta = db.relationship("Ruta")
    vehiculo_default = db.relationship("Vehiculo")
    conductor_default = db.relationship("Conductor")


class ProgramacionViaje(db.Model):
    __tablename__ = "programacion_viaje"
    __table_args__ = (db.UniqueConstraint("id_horario", "fecha_salida", name="uk_horario_fecha"),)

    id_viaje = db.Column(db.Integer, primary_key=True)
    id_horario = db.Column(db.Integer, db.ForeignKey("horarios.id_horario"), nullable=False)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey("vehiculo.id_vehiculo"))
    id_conductor = db.Column(db.Integer, db.ForeignKey("conductor.id_conductor"))
    fecha_salida = db.Column(db.Date, nullable=False)
    salida_programada = db.Column(db.DateTime, nullable=False)
    salida_real = db.Column(db.DateTime)
    llegada_programada = db.Column(db.DateTime, nullable=False)
    llegada_real = db.Column(db.DateTime)
    precio_pasaje = db.Column(db.Numeric(8, 2), nullable=False)
    estado_viaje = db.Column(
        db.Enum("Programado", "En Ruta", "Finalizado", "Cancelado", name="viaje_estado"),
        nullable=False, default="Programado")
    clima = db.Column(db.String(30))
    es_feriado = db.Column(db.Boolean, nullable=False, default=False)

    horario = db.relationship("Horario")
    vehiculo = db.relationship("Vehiculo")
    conductor = db.relationship("Conductor")
    pasajes = db.relationship("DetallePasaje", back_populates="viaje")
    encomiendas = db.relationship("DetalleEncomienda", back_populates="viaje")
    incidentes = db.relationship("IncidenteRuta", back_populates="viaje")

    @property
    def vehiculo_efectivo(self):
        """Retorna el vehículo asignado al viaje o, en su defecto, el vehículo por defecto del horario."""
        return self.vehiculo or (self.horario.vehiculo_default if self.horario else None)

    @property
    def pasajes_activos(self):
        return [p for p in self.pasajes if p.estado != "anulado"]

    @property
    def asientos_libres(self):
        v = self.vehiculo_efectivo
        cap = v.capacidad_asientos if v else 0
        return max(0, cap - len(self.pasajes_activos))

    @property
    def minutos_retraso_llegada(self):
        if self.llegada_real and self.llegada_programada:
            return int((self.llegada_real - self.llegada_programada).total_seconds() // 60)
        return None


# =====================================================================
# 4. VENTAS
# =====================================================================
class ReservaVenta(db.Model):
    __tablename__ = "reservas_ventas"

    id_reserva = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("clientes.id_cliente"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"))
    id_sede = db.Column(db.Integer, db.ForeignKey("sedes.id_sede", ondelete="SET NULL"))
    fecha_emision = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    metodo_pago = db.Column(
        db.Enum("efectivo", "yape", "plin", "tarjeta", "transferencia", name="venta_metodo"),
        nullable=False, default="efectivo")
    canal_venta = db.Column(db.Enum("terminal", "web", "app", name="venta_canal"),
                            nullable=False, default="terminal")
    tipo_comprobante = db.Column(db.Enum("boleta", "factura", "ticket", name="venta_comprobante"),
                                 nullable=False, default="boleta")
    estado = db.Column(db.Enum("pagada", "anulada", name="venta_estado"),
                       nullable=False, default="pagada")

    cliente = db.relationship("Cliente")
    usuario = db.relationship("Usuario")
    sede = db.relationship("Sede")
    pasajes = db.relationship("DetallePasaje", back_populates="reserva")
    encomiendas = db.relationship("DetalleEncomienda", back_populates="reserva")


class DetallePasaje(db.Model):
    __tablename__ = "detalle_pasajes"

    id_detalle_pasaje = db.Column(db.Integer, primary_key=True)
    id_reserva = db.Column(db.Integer, db.ForeignKey("reservas_ventas.id_reserva"), nullable=False)
    id_viaje = db.Column(db.Integer, db.ForeignKey("programacion_viaje.id_viaje"), nullable=False)
    numero_asiento = db.Column(db.Integer, nullable=False)
    dni_pasajero = db.Column(db.String(8), nullable=False)
    nombre_pasajero = db.Column(db.String(150), nullable=False)
    fecha_nacimiento = db.Column(db.Date)
    sexo = db.Column(db.Enum("M", "F", "otro", name="pasaje_sexo"))
    precio_pagado = db.Column(db.Numeric(8, 2), nullable=False)
    estado = db.Column(db.Enum("vendido", "abordado", "anulado", "no_show", name="pasaje_estado"),
                       nullable=False, default="vendido")
    # Columna generada por MySQL: NO se inserta ni se actualiza desde Python.
    asiento_activo = db.Column(
        db.Integer,
        db.Computed("CASE WHEN estado = 'anulado' THEN NULL ELSE numero_asiento END",
                    persisted=True))

    reserva = db.relationship("ReservaVenta", back_populates="pasajes")
    viaje = db.relationship("ProgramacionViaje", back_populates="pasajes")


class DetalleEncomienda(db.Model):
    __tablename__ = "detalle_encomiendas"

    id_detalle_encomienda = db.Column(db.Integer, primary_key=True)
    id_reserva = db.Column(db.Integer, db.ForeignKey("reservas_ventas.id_reserva"), nullable=False)
    id_viaje = db.Column(db.Integer, db.ForeignKey("programacion_viaje.id_viaje"), nullable=False)
    dni_destinatario = db.Column(db.String(8), nullable=False)
    nombre_destinatario = db.Column(db.String(150), nullable=False)
    telefono_destinatario = db.Column(db.String(15), nullable=False)
    descripcion_contenido = db.Column(db.Text, nullable=False)
    peso_kg = db.Column(db.Numeric(6, 2), nullable=False)
    clave_recojo = db.Column(db.String(10), nullable=False)
    estado_entrega = db.Column(
        db.Enum("Registrado", "En transito", "Entregado", "Perdido", name="encomienda_estado"),
        nullable=False, default="Registrado")
    precio_pagado = db.Column(db.Numeric(8, 2), nullable=False)
    entregado_en = db.Column(db.DateTime)

    reserva = db.relationship("ReservaVenta", back_populates="encomiendas")
    viaje = db.relationship("ProgramacionViaje", back_populates="encomiendas")


# =====================================================================
# 5. DATOS OPERATIVOS PARA ML
# =====================================================================
class IncidenteRuta(db.Model):
    __tablename__ = "incidentes_ruta"

    id_incidente = db.Column(db.Integer, primary_key=True)
    id_viaje = db.Column(db.Integer, db.ForeignKey("programacion_viaje.id_viaje"), nullable=False)
    tipo_incidente = db.Column(
        db.Enum("falla_mecanica", "accidente", "bloqueo_via", "clima", "retraso", "otro",
                name="incidente_tipo"), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    lugar_referencial = db.Column(db.String(150), nullable=False)
    fecha_hora = db.Column(db.DateTime, nullable=False, server_default=func.current_timestamp())
    minutos_retraso_estimado = db.Column(db.Integer, nullable=False, default=0)

    viaje = db.relationship("ProgramacionViaje", back_populates="incidentes")


class Mantenimiento(db.Model):
    __tablename__ = "mantenimientos"

    id_mantenimiento = db.Column(db.Integer, primary_key=True)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey("vehiculo.id_vehiculo"), nullable=False)
    tipo = db.Column(db.Enum("preventivo", "correctivo", name="mant_tipo"), nullable=False)
    descripcion = db.Column(db.String(200))
    fecha = db.Column(db.Date, nullable=False)
    km_al_momento = db.Column(db.Integer, nullable=False)
    costo = db.Column(db.Numeric(9, 2), nullable=False, default=0)
    dias_inoperativo = db.Column(db.Integer, nullable=False, default=0)

    vehiculo = db.relationship("Vehiculo")


class Combustible(db.Model):
    __tablename__ = "combustible"

    id_carga = db.Column(db.Integer, primary_key=True)
    id_vehiculo = db.Column(db.Integer, db.ForeignKey("vehiculo.id_vehiculo"), nullable=False)
    id_viaje = db.Column(db.Integer, db.ForeignKey("programacion_viaje.id_viaje"))
    fecha = db.Column(db.DateTime, nullable=False)
    galones = db.Column(db.Numeric(7, 2), nullable=False)
    costo_total = db.Column(db.Numeric(8, 2), nullable=False)
    km_odometro = db.Column(db.Integer, nullable=False)

    vehiculo = db.relationship("Vehiculo")
    viaje = db.relationship("ProgramacionViaje")


# =====================================================================
# 6. VISTAS (solo lectura) - útiles para ML y reportes
# =====================================================================
def dataset_ocupacion():
    """Devuelve las filas de v_dataset_ocupacion como lista de dicts.
    Para pandas:  pd.read_sql("SELECT * FROM v_dataset_ocupacion", db.engine)
    """
    from sqlalchemy import text
    with db.engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM v_dataset_ocupacion"))
        return [dict(r._mapping) for r in res]