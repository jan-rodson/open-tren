-- Schema para Open Tren (simplificado)
-- 2 tablas: circulaciones, rutas

-- Tabla de rutas
CREATE TABLE IF NOT EXISTS rutas (
    route_id TEXT PRIMARY KEY,
    tipo_servicio TEXT NOT NULL,
    origen_nombre TEXT NOT NULL,
    destino_nombre TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rutas_tipo ON rutas (tipo_servicio);

-- Tabla de circulaciones (viajes individuales)
CREATE TABLE IF NOT EXISTS circulaciones (
    trip_id TEXT PRIMARY KEY,
    codigo_tren TEXT NOT NULL,
    fecha DATE NOT NULL,
    route_id TEXT NOT NULL REFERENCES rutas (route_id),
    hora_salida TIME NOT NULL,
    hora_llegada TIME NOT NULL,
    delay_segundos INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para filtros de la UI
CREATE INDEX IF NOT EXISTS idx_circ_fecha ON circulaciones (fecha);
CREATE INDEX IF NOT EXISTS idx_circ_hora_salida ON circulaciones (hora_salida);
CREATE INDEX IF NOT EXISTS idx_circ_route_id ON circulaciones (route_id);

-- Índice para queries de retrasos
CREATE INDEX IF NOT EXISTS idx_circ_delay ON circulaciones (delay_segundos)
    WHERE delay_segundos > 300;

-- Índice para agrupar por trayecto-tipo
CREATE INDEX IF NOT EXISTS idx_circ_trayecto ON circulaciones (
    codigo_tren,
    fecha,
    hora_salida
);
