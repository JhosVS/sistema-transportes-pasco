-- 1. CREACIÓN DE LA BASE DE DATOS
DROP DATABASE IF EXISTS bd_transporte_pasco;
CREATE DATABASE bd_transporte_pasco;
USE bd_transporte_pasco;

-- 2. TABLAS PRINCIPALES (CATÁLOGOS)

-- Sedes / Terminales
CREATE TABLE sedes (
    id_sede INT AUTO_INCREMENT PRIMARY KEY,
    nombre_sede VARCHAR(100) NOT NULL,
    direccion VARCHAR(200) NOT NULL,
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8)
);

-- Usuarios (administradores, operadores, etc.)
CREATE TABLE usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    id_sede INT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_sede FOREIGN KEY (id_sede) REFERENCES sedes(id_sede) ON DELETE SET NULL
);

-- Vehículos
CREATE TABLE vehiculo (
    id_vehiculo INT AUTO_INCREMENT PRIMARY KEY,
    placa VARCHAR(10) NOT NULL UNIQUE,
    marca VARCHAR(50) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    color VARCHAR(30) NOT NULL,
    capacidad_asientos INT NOT NULL,
    capacidad_carga_kg DECIMAL(8, 2) NOT NULL,
    estado VARCHAR(20) DEFAULT 'Disponible'
);

-- Conductores
CREATE TABLE conductor (
    id_conductor INT AUTO_INCREMENT PRIMARY KEY,
    dni VARCHAR(8) NOT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    telefono VARCHAR(15) NOT NULL,
    licencia_conducir VARCHAR(15) NOT NULL UNIQUE,
    estado VARCHAR(20) DEFAULT 'Activo'
);

-- Clientes
CREATE TABLE clientes (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    num_documento VARCHAR(12) NOT NULL UNIQUE,
    nombres_razon_social VARCHAR(150) NOT NULL,
    telefono VARCHAR(15) NOT NULL,
    email VARCHAR(100)
);

-- 3. RUTAS Y PROGRAMACIÓN DE VIAJES

-- Rutas
CREATE TABLE rutas (
    id_ruta INT AUTO_INCREMENT PRIMARY KEY,
    id_sede_origen INT NOT NULL,
    id_sede_destino INT NOT NULL,
    duracion_estimada_hrs DECIMAL(4, 2) NOT NULL,
    FOREIGN KEY (id_sede_origen) REFERENCES sedes(id_sede),
    FOREIGN KEY (id_sede_destino) REFERENCES sedes(id_sede)
);

-- horarios
CREATE TABLE horarios (
    id_horario INT AUTO_INCREMENT PRIMARY KEY,
    id_ruta INT NOT NULL,
    id_vehiculo INT NOT NULL,
    id_conductor INT NOT NULL,
    dia_semana ENUM('Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo') NOT NULL,
    hora_salida TIME NOT NULL,
    precio_pasaje_base DECIMAL(8, 2) NOT NULL,
    precio_kg_carga_base DECIMAL(8, 2) NOT NULL,
    estado ENUM('Activo', 'Inactivo') DEFAULT 'Activo',
    FOREIGN KEY (id_ruta) REFERENCES rutas(id_ruta),
    FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo),
    FOREIGN KEY (id_conductor) REFERENCES conductor(id_conductor)
);

-- Programación de Viajes
CREATE TABLE programacion_viaje (
    id_viaje INT AUTO_INCREMENT PRIMARY KEY,
    id_horario INT NOT NULL,                  -- Enlace a la plantilla
    fecha_salida DATE NOT NULL,                -- La fecha exacta (ej: 2026-10-02)
    estado_viaje ENUM('Programado', 'En Ruta', 'Finalizado', 'Cancelado') DEFAULT 'Programado',
    FOREIGN KEY (id_horario) REFERENCES horarios(id_horario),
    CONSTRAINT uk_horario_fecha UNIQUE (id_horario, fecha_salida) -- Evita crear el mismo viaje 2 veces el mismo día
);

-- 4. RESERVAS Y BOLETOS

-- Cabecera de Ventas
CREATE TABLE reservas_ventas (
    id_reserva INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    fecha_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
    monto_total DECIMAL(10, 2) NOT NULL,
    metodo_pago VARCHAR(30) NOT NULL,
    tipo_comprobante VARCHAR(20) NOT NULL,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
);

-- Detalle de Pasajes (evita duplicar el mismo asiento en un mismo viaje)
CREATE TABLE detalle_pasajes (
    id_detalle_pasaje INT AUTO_INCREMENT PRIMARY KEY,
    id_reserva INT NOT NULL,
    id_viaje INT NOT NULL,
    numero_asiento INT NOT NULL,
    dni_pasajero VARCHAR(8) NOT NULL,
    nombre_pasajero VARCHAR(150) NOT NULL,
    precio_pagado DECIMAL(8, 2) NOT NULL,
    FOREIGN KEY (id_reserva) REFERENCES reservas_ventas(id_reserva),
    FOREIGN KEY (id_viaje) REFERENCES programacion_viaje(id_viaje),
    CONSTRAINT uk_viaje_asiento UNIQUE (id_viaje, numero_asiento)
);

-- Detalle de Encomiendas
CREATE TABLE detalle_encomiendas (
    id_detalle_encomienda INT AUTO_INCREMENT PRIMARY KEY,
    id_reserva INT NOT NULL,
    id_viaje INT NOT NULL,
    dni_destinatario VARCHAR(8) NOT NULL,
    nombre_destinatario VARCHAR(150) NOT NULL,
    telefono_destinatario VARCHAR(15) NOT NULL,
    descripcion_contenido TEXT NOT NULL,
    peso_kg DECIMAL(6, 2) NOT NULL,
    clave_recojo VARCHAR(10) NOT NULL,
    estado_entrega VARCHAR(30) DEFAULT 'Registrado',
    precio_pagado DECIMAL(8, 2) NOT NULL,
    FOREIGN KEY (id_reserva) REFERENCES reservas_ventas(id_reserva),
    FOREIGN KEY (id_viaje) REFERENCES programacion_viaje(id_viaje)
);

-- 5. INCIDENTES EN RUTA

CREATE TABLE incidentes_ruta (
    id_incidente INT AUTO_INCREMENT PRIMARY KEY,
    id_viaje INT NOT NULL,
    tipo_incidente VARCHAR(50) NOT NULL,
    descripcion TEXT NOT NULL,
    lugar_referencial VARCHAR(150) NOT NULL,
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
    minutos_retraso_estimado INT DEFAULT 0,
    FOREIGN KEY (id_viaje) REFERENCES programacion_viaje(id_viaje)
);