use bd_transporte_pasco;
-- ============================================================
-- 1. REGISTRO DE SEDES (Base Principal: Cerro de Pasco)
-- ============================================================
INSERT INTO sedes (nombre_sede, direccion, latitud, longitud) VALUES
('Terminal Cerro de Pasco', 'Av. Minerales 123, Chaupimarca, Cerro de Pasco', -10.683333, -76.256667), -- id_sede = 1
('Agencia Lima - La Victoria', 'Av. 28 de Julio 1420, La Victoria, Lima', -12.062100, -77.021100),    -- id_sede = 2
('Agencia Huancayo', 'Av. Ferrocarril 850, Huancayo', -12.065300, -75.204800),                     -- id_sede = 3
('Agencia Huánuco', 'Jr. General Prado 450, Huánuco', -9.930600, -76.242200);                       -- id_sede = 4


-- ============================================================
-- 2. REGISTRO DE VEHÍCULOS (Buses asignados a sus sedes actuales)
-- ============================================================
INSERT INTO vehiculo (placa, marca, modelo, color, capacidad_asientos, capacidad_carga_kg, estado) VALUES
('C1A-750', 'Mercedes-Benz', 'O-500R', 'Azul/Blanco', 44, 1200.00, 'Disponible'), -- En Cerro de Pasco
('B8M-910', 'Volvo', 'B450R', 'Rojo/Plata', 48, 1500.00, 'Disponible'),         -- En Cerro de Pasco
('F5T-320', 'Scania', 'K360', 'Blanco', 40, 1000.00, 'Disponible'),               -- En Lima
('A2K-110', 'Hyundai', 'Universe', 'Gris', 36, 800.00, 'Disponible');             -- En Huancayo


-- ============================================================
-- 3. REGISTRO DE CONDUCTORES (Con categoría de brevete MTC A-IIIc)
-- ============================================================
INSERT INTO conductor (dni, nombres, apellidos, telefono, licencia_conducir) VALUES
('45892134', 'Juan Carlos', 'Pérez Quispe', '963852741', 'Q45892134-A3'), -- En Cerro de Pasco
('70123456', 'Ronaldo', 'Espinoza Ramos', '987654321', 'E70123456-A3'),   -- En Cerro de Pasco
('10293847', 'Wilder', 'López Tacuri', '951753852', 'L10293847-A3'),      -- En Lima
('25364758', 'Héctor', 'Chávez Meléndez', '912345678', 'C25364758-A3');   -- En Huancayo


-- ============================================================
-- 4. REGISTRO DE RUTAS (Ida y Vuelta desde/hacia Cerro de Pasco)
-- ============================================================
INSERT INTO rutas (id_sede_origen, id_sede_destino, duracion_estimada_hrs) VALUES
-- Conexión Pasco - Lima
(1, 2, 7.50), -- Pasco -> Lima (id_ruta = 1)
(2, 1, 7.50), -- Lima -> Pasco (id_ruta = 2)

-- Conexión Pasco - Huancayo
(1, 3, 5.00), -- Pasco -> Huancayo (id_ruta = 3)
(3, 1, 5.00), -- Huancayo -> Pasco (id_ruta = 4)

-- Conexión Pasco - Huánuco
(1, 4, 3.50), -- Pasco -> Huánuco (id_ruta = 5)
(4, 1, 3.50); -- Huánuco -> Pasco (id_ruta = 6)

-- ============================================================
-- 5. REGISTRO DE USUARIOS (Administrador Principal)
-- ============================================================
INSERT INTO usuarios (nombre, email, password, estado, id_sede) 
VALUES (
    'Administrador Principal', 
    'admin@transportes.com', 
    'admin123', 
    'Activo', 
    1
);

-- ============================================================
-- 6. REGISTRO DE HORARIOS RECURRENTES COHERENTES
-- ============================================================

-- ------------------------------------------------------------
-- RUTA 1 & 2: PASCO ⇄ LIMA (Scania K360 / Wilder López)
-- ------------------------------------------------------------
-- Salida Pasco -> Lima (Viernes 08:00 PM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (1, 3, 3, 'Viernes', '20:00:00', 50.00, 3.50, 'Activo');

-- Retorno Lima -> Pasco (Domingo 10:00 PM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (2, 3, 3, 'Domingo', '22:00:00', 55.00, 3.50, 'Activo');


-- ------------------------------------------------------------
-- RUTA 3 & 4: PASCO ⇄ HUANCAYO (Hyundai Universe / Héctor Chávez)
-- ------------------------------------------------------------
-- Salida Pasco -> Huancayo (Lunes 06:00 AM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (3, 4, 4, 'Lunes', '06:00:00', 30.00, 2.00, 'Activo');

-- Retorno Huancayo -> Pasco (Martes 03:00 PM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (4, 4, 4, 'Martes', '15:00:00', 30.00, 2.00, 'Activo');

-- Salida Pasco -> Huancayo (Jueves 06:00 AM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (3, 4, 4, 'Jueves', '06:00:00', 30.00, 2.00, 'Activo');

-- Retorno Huancayo -> Pasco (Viernes 02:00 PM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (4, 4, 4, 'Viernes', '14:00:00', 30.00, 2.00, 'Activo');


-- ------------------------------------------------------------
-- RUTA 5 & 6: PASCO ⇄ HUÁNUCO (Mercedes-Benz / Juan Carlos Pérez)
-- ------------------------------------------------------------
-- Salida Pasco -> Huánuco (Viernes 06:00 AM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (5, 1, 1, 'Viernes', '06:00:00', 35.00, 2.50, 'Activo');

-- Retorno Huánuco -> Pasco (Lunes 04:00 AM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (6, 1, 1, 'Lunes', '04:00:00', 35.00, 2.50, 'Activo');


-- ------------------------------------------------------------
-- RUTA 5 & 6: PASCO ⇄ HUÁNUCO (Volvo B450R / Ronaldo Espinoza)
-- ------------------------------------------------------------
-- Salida Pasco -> Huánuco (Miércoles 07:00 AM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (5, 2, 2, 'Miercoles', '07:00:00', 35.00, 2.50, 'Activo');

-- Retorno Huánuco -> Pasco (Jueves 05:00 PM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (6, 2, 2, 'Jueves', '17:00:00', 35.00, 2.50, 'Activo');

-- Salida Pasco -> Huánuco (Sábado 01:00 PM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (5, 2, 2, 'Sabado', '13:00:00', 40.00, 2.50, 'Activo');

-- Retorno Huánuco -> Pasco (Domingo 06:00 PM)
INSERT INTO horarios (id_ruta, id_vehiculo, id_conductor, dia_semana, hora_salida, precio_pasaje_base, precio_kg_carga_base, estado)
VALUES (6, 2, 2, 'Domingo', '18:00:00', 40.00, 2.50, 'Activo');

SELECT 
    pv.id_viaje,
    pv.fecha_salida,
    DAYNAME(pv.fecha_salida) AS nombre_dia_semana,
    WEEKDAY(pv.fecha_salida) AS dia_semana_num, -- 0=Lunes, 6=Domingo
    MONTH(pv.fecha_salida) AS mes,
    DAY(pv.fecha_salida) AS dia_mes,
    CASE WHEN WEEKDAY(pv.fecha_salida) IN (4, 5, 6) THEN 1 ELSE 0 END AS es_fin_semana,
    h.id_ruta,
    r.id_sede_origen,
    r.id_sede_destino,
    TIME_TO_SEC(h.hora_salida) / 3600 AS hora_salida_decimal,
    h.precio_pasaje_base,
    v.capacidad_asientos,
    COUNT(dp.id_detalle_pasaje) AS pasajes_vendidos
FROM programacion_viaje pv
INNER JOIN horarios h ON pv.id_horario = h.id_horario
INNER JOIN rutas r ON h.id_ruta = r.id_ruta
INNER JOIN vehiculo v ON h.id_vehiculo = v.id_vehiculo
LEFT JOIN detalle_pasajes dp ON pv.id_viaje = dp.id_viaje
GROUP BY 
    pv.id_viaje, 
    pv.fecha_salida, 
    h.id_ruta, 
    r.id_sede_origen, 
    r.id_sede_destino, 
    h.hora_salida, 
    h.precio_pasaje_base, 
    v.capacidad_asientos
ORDER BY pv.fecha_salida ASC;