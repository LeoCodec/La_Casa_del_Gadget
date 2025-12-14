-- TIPOS DE EMPLEADO (admin, gerente, ventas, inventario, etc.)
CREATE TABLE IF NOT EXISTS tipos_empleado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL
);

-- USUARIOS (empleados y clientes, diferenciados por rol y tipo_empleado)
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    contraseña TEXT NOT NULL,
    rol TEXT NOT NULL, -- admin, cliente, ventas, inventario, etc.
    tipo_empleado_id INTEGER,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo_empleado_id) REFERENCES tipos_empleado(id)
);

-- TOKENS DE SESIÓN (para controlar logins, expiración, etc.)
CREATE TABLE IF NOT EXISTS tokens_sesion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    ip TEXT,
    user_agent TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMP NOT NULL,
    activo BOOLEAN DEFAULT 1,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- PRODUCTOS (catálogo general de gadgets)
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    marca TEXT NOT NULL,
    tipo TEXT NOT NULL,          -- Smartphone, Laptop, Consola, etc.
    color TEXT,
    almacenamiento TEXT,
    precio REAL,
    descripcion TEXT,
    url_imagen TEXT,
    disponible BOOLEAN DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SERVICIOS (por ejemplo: formateo, instalación de software, garantías, etc.)
CREATE TABLE IF NOT EXISTS servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    precio REAL
);

-- INVENTARIO (stock por sucursal)
CREATE TABLE IF NOT EXISTS inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    sucursal TEXT NOT NULL, -- Centro, Polanco, Satélite, etc.
    stock INTEGER DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

-- CARRITO (items agregados por usuario antes de concretar venta)
CREATE TABLE IF NOT EXISTS carrito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    servicio_id INTEGER,
    cantidad INTEGER DEFAULT 1,
    agregado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (servicio_id) REFERENCES servicios(id)
);

-- VENTAS (encabezado de la venta)
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL, -- cliente
    empleado_id INTEGER,         -- empleado que atendió (cajero / ventas)
    total REAL,
    metodo_pago TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (empleado_id) REFERENCES usuarios(id)
);

-- DETALLE DE VENTA (líneas de productos/servicios vendidos)
CREATE TABLE IF NOT EXISTS detalle_venta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    servicio_id INTEGER,
    cantidad INTEGER DEFAULT 1,
    precio REAL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (servicio_id) REFERENCES servicios(id)
);

-- CITAS (para agendar pruebas de productos)
CREATE TABLE IF NOT EXISTS citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL, -- cliente
    empleado_id INTEGER,         -- empleado que atiende la cita
    fecha_hora TIMESTAMP NOT NULL,
    estado TEXT DEFAULT 'pendiente',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (empleado_id) REFERENCES usuarios(id)
);

-- PRODUCTOS ASOCIADOS A UNA CITA (qué productos se probarán)
CREATE TABLE IF NOT EXISTS cita_productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cita_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    servicio_id INTEGER,
    confirmado BOOLEAN DEFAULT 0,
    FOREIGN KEY (cita_id) REFERENCES citas(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (servicio_id) REFERENCES servicios(id)
);

-- REGISTRO DE CAMBIOS DE INVENTARIO (para dashboard/admin)
CREATE TABLE IF NOT EXISTS registro_inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inventario_id INTEGER NOT NULL,
    cambio INTEGER NOT NULL, -- positivo: entrada, negativo: salida
    motivo TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inventario_id) REFERENCES inventario(id)
);
