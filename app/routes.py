from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
import sqlite3
import os
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

main = Blueprint("main", __name__)

# =========================================================
# DB CONEXIONES
# - gadget.db (productos, inventario, etc.) -> current_app.config["DATABASE"]
# - empleados.db (staff login) -> database/empleados.db
# =========================================================

def get_conn():
    """Conexión a gadget.db (tu base principal)."""
    conn = sqlite3.connect(current_app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn

def get_staff_conn():
    """Conexión a empleados.db (staff/admin)."""
    db_path = os.path.join(current_app.root_path, "..", "database", "empleados.db")
    db_path = os.path.abspath(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# HELPERS PRODUCTOS / INVENTARIO (gadget.db)
# =========================================================

def fetch_all_products(limit=None):
    conn = get_conn()
    cur = conn.cursor()
    sql = """
        SELECT id, nombre, marca, tipo, precio, descripcion, url_imagen, disponible
        FROM productos
        WHERE disponible = 1
        ORDER BY id ASC
    """
    params = []
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def fetch_marcas_disponibles():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT marca
        FROM productos
        WHERE disponible = 1
        ORDER BY marca ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [r["marca"] for r in rows]

def fetch_max_precio():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(MAX(precio), 0) AS max_precio
        FROM productos
        WHERE disponible = 1
    """)
    row = cur.fetchone()
    conn.close()
    try:
        return int(float(row["max_precio"] or 0))
    except:
        return 0

def get_stock_total(producto_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(stock), 0) AS stock_total
        FROM inventario
        WHERE producto_id = ?
    """, (producto_id,))
    row = cur.fetchone()
    conn.close()
    return int(row["stock_total"] or 0)

def get_producto_basico(producto_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nombre, marca, tipo, precio, url_imagen, disponible
        FROM productos
        WHERE id = ? AND disponible = 1
    """, (producto_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# =========================================================
# HELPERS SESIÓN / CONTADORES
# =========================================================

def get_cart_count():
    """Total de piezas en carrito (suma cantidades)."""
    carrito = session.get("carrito", [])
    total = 0
    for item in carrito:
        try:
            total += int(item.get("cantidad", 1))
        except:
            total += 1
    return total


# =========================================================
# RUTAS PÚBLICAS
# =========================================================

@main.route("/")
def index():
    productos_destacados = fetch_all_products(limit=8)
    return render_template(
        "index.html",
        productos_destacados=productos_destacados,
        cart_count=get_cart_count()
    )

@main.route("/probar-producto", methods=["GET", "POST"])
def probar_producto():
    # Si luego quieres guardar la cita en DB, aquí es.
    return render_template("citas.html", cart_count=get_cart_count())

@main.route("/login", methods=["GET", "POST"])
def login():
    # Login cliente (si lo implementas después)
    return render_template("login.html", cart_count=get_cart_count())

@main.route("/register", methods=["GET", "POST"])
def register():
    # Registro cliente (si lo implementas después)
    return render_template("register.html", cart_count=get_cart_count())

# Antes tu ruta /empleados rendereaba template directo;
# Ahora la unimos con la lógica de tu compa:
@main.route("/empleados")
def empleados():
    # Si ya es staff, redirige según rol
    if "user_id" in session and session.get("tipo_usuario") == "staff":
        rol = session.get("user_rol")
        if rol in ("empleado", "cajero"):
            return redirect(url_for("main.punto_venta"))
        return redirect(url_for("main.admin_dashboard"))

    # si no, al login staff
    return redirect(url_for("main.admin_login"))


# =========================================================
# ✅ PRODUCTOS + FILTROS (ruta única /productos)
# =========================================================

@main.route("/productos")
def productos_listado():
    # Tipos “principales” (lo que NO debe caer en accesorios)
    tipos_principales = ["Smartphone", "Laptop", "Tablet"]

    categorias = request.args.getlist("categoria")  # checkboxes
    marcas = request.args.getlist("marca")
    q = (request.args.get("q") or "").strip()
    precio_max = request.args.get("precio_max")

    try:
        precio_max_num = float(precio_max) if precio_max not in (None, "") else None
    except ValueError:
        precio_max_num = None

    where = ["disponible = 1"]
    params = []

    # --- Categorías ---
    # telefonos -> Smartphone
    # laptops -> Laptop
    # tablets -> Tablet
    # wearables -> Wearable (si existe en BD)
    # accesorios -> TODO lo demás (drones, cámaras, consolas, audio, etc.)
    tipos_in = []
    accesorios_activado = False

    for cat in categorias:
        if cat == "telefonos":
            tipos_in.append("Smartphone")
        elif cat == "laptops":
            tipos_in.append("Laptop")
        elif cat == "tablets":
            tipos_in.append("Tablet")
        elif cat == "wearables":
            tipos_in.append("Wearable")
        elif cat == "accesorios":
            accesorios_activado = True

    tipos_in = sorted(set(tipos_in))

    # Caso especial: accesorios = "todo lo demás"
    # Si usuario selecciona accesorios + alguna categoría principal -> OR
    if accesorios_activado and tipos_in:
        where.append(
            "("
            + f"tipo IN ({','.join(['?']*len(tipos_in))})"
            + " OR "
            + f"tipo NOT IN ({','.join(['?']*len(tipos_principales))})"
            + ")"
        )
        params.extend(tipos_in)
        params.extend(tipos_principales)

    elif accesorios_activado and not tipos_in:
        where.append(f"tipo NOT IN ({','.join(['?']*len(tipos_principales))})")
        params.extend(tipos_principales)

    elif (not accesorios_activado) and tipos_in:
        where.append(f"tipo IN ({','.join(['?']*len(tipos_in))})")
        params.extend(tipos_in)

    # Si no seleccionó categoría -> no agregamos filtro y se muestra TODO.

    # --- Marca ---
    if marcas:
        where.append(f"marca IN ({','.join(['?']*len(marcas))})")
        params.extend(marcas)

    # --- Búsqueda ---
    if q:
        where.append("(nombre LIKE ? OR marca LIKE ? OR tipo LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    # --- Precio ---
    if precio_max_num is not None:
        where.append("precio <= ?")
        params.append(precio_max_num)

    sql = f"""
        SELECT id, nombre, marca, tipo, precio, descripcion, url_imagen, disponible
        FROM productos
        WHERE {" AND ".join(where)}
        ORDER BY id ASC
    """

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    productos = [dict(r) for r in cur.fetchall()]
    conn.close()

    ui_data = {
        "marcas_disponibles": fetch_marcas_disponibles(),
        "max_precio_real": max(fetch_max_precio(), 50000),
    }

    filtros = {
        "categorias": categorias,
        "marcas": marcas,
        "q": q,
        "precio_max": precio_max_num if precio_max_num is not None else ui_data["max_precio_real"],
    }

    return render_template(
        "producto_detalle.html",
        productos=productos,
        filtros=filtros,
        ui_data=ui_data,
        cart_count=get_cart_count()
    )


# =========================================================
# ✅ CARRITO (gadget.db)
# =========================================================

@main.route("/carrito", methods=["GET"])
def carrito():
    carrito = session.get("carrito", [])

    # normalizar
    for item in carrito:
        item["precio"] = float(item.get("precio", 0))
        item["cantidad"] = int(item.get("cantidad", 1))

    subtotal = sum(item["precio"] * item["cantidad"] for item in carrito)
    total = subtotal

    return render_template(
        "carrito.html",
        carrito=carrito,
        subtotal=subtotal,
        total=total,
        cart_count=get_cart_count()
    )

@main.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    producto = get_producto_basico(producto_id)
    if not producto:
        return redirect(url_for("main.productos_listado"))

    stock_total = get_stock_total(producto_id)
    if stock_total <= 0:
        flash("Sin stock disponible para este producto.", "warning")
        return redirect(url_for("main.productos_listado"))

    carrito = session.get("carrito", [])

    # normalizar
    for item in carrito:
        item["cantidad"] = int(item.get("cantidad", 1))
        item["precio"] = float(item.get("precio", 0))

    # si ya existe, sumar (con límite)
    for item in carrito:
        if item["id"] == producto_id:
            nuevo = item["cantidad"] + 1
            if nuevo <= min(10, stock_total):
                item["cantidad"] = nuevo
            session["carrito"] = carrito
            return redirect(url_for("main.carrito"))

    # si no existe, agregar
    carrito.append({
        "id": int(producto["id"]),
        "nombre": producto["nombre"],
        "marca": producto["marca"],
        "tipo": producto["tipo"],
        "precio": float(producto["precio"] or 0),
        "url_imagen": producto.get("url_imagen"),
        "cantidad": 1,
    })

    session["carrito"] = carrito
    return redirect(url_for("main.carrito"))

@main.route("/carrito/actualizar/<int:producto_id>", methods=["POST"])
def actualizar_carrito(producto_id):
    accion = request.form.get("accion")  # sumar/restar
    carrito = session.get("carrito", [])
    stock_total = get_stock_total(producto_id)

    for item in carrito:
        if item["id"] == producto_id:
            item["cantidad"] = int(item.get("cantidad", 1))

            if accion == "sumar":
                if item["cantidad"] < min(10, stock_total):
                    item["cantidad"] += 1

            elif accion == "restar":
                if item["cantidad"] > 1:
                    item["cantidad"] -= 1
            break

    session["carrito"] = carrito
    return redirect(url_for("main.carrito"))

@main.route("/carrito/eliminar/<int:producto_id>", methods=["POST"])
def eliminar_carrito(producto_id):
    carrito = session.get("carrito", [])
    carrito = [item for item in carrito if item["id"] != producto_id]
    session["carrito"] = carrito
    return redirect(url_for("main.carrito"))

@main.route("/carrito/pagar", methods=["POST"])
def pagar():
    # Simulación (luego aquí insertas venta + detalle_venta)
    session["carrito"] = []
    return "<h1>¡Pago procesado! (Simulación)</h1>"


# =========================================================
# ✅ STAFF / ADMIN (empleados.db)
# =========================================================

@main.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("contraseña", "")

        try:
            conn = get_staff_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM empleados WHERE username = ?", (usuario,))
            user = cur.fetchone()
            conn.close()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["nombre_completo"] = user["nombre_completo"] if "nombre_completo" in user.keys() else user["username"]
                session["user_rol"] = user["rol"]
                session["tipo_usuario"] = "staff"
                session["fecha_hoy"] = datetime.now().strftime("%d/%m/%Y")

                # empleado/cajero -> caja, admin/gerente -> dashboard
                if user["rol"] in ("empleado", "cajero"):
                    return redirect(url_for("main.punto_venta"))
                return redirect(url_for("main.admin_dashboard"))

            flash("Credenciales incorrectas", "error")

        except Exception as e:
            print(f"Error Login: {e}")
            flash("Error de conexión", "error")

    return render_template("admin/login.html", cart_count=get_cart_count())

@main.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))

@main.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session or session.get("tipo_usuario") != "staff":
        return redirect(url_for("main.admin_login"))

    # KPIs simulados
    datos_kpi = {
        "ventas_dia": 45230,
        "citas_hoy": 8,
        "stock_bajo": 5,
        "empleado_mes": "Leo Cruz",
        "fecha_hoy": datetime.now().strftime("%d/%m/%Y"),
    }

    ultimas_ventas = [
        {"fecha": "11/12/2025", "vendedor": "Cajero 1", "producto": "iPhone 15", "total": 28999},
        {"fecha": "11/12/2025", "vendedor": "Leo Cruz", "producto": "AirPods Pro", "total": 5999},
    ]

    ultimas_citas = [
        {"hora": "10:00 AM", "cliente": "Ana López", "producto": "MacBook Air", "estado": "Confirmada"},
        {"hora": "12:30 PM", "cliente": "Carlos Ruiz", "producto": "Galaxy S24", "estado": "Pendiente"},
    ]

    return render_template(
        "admin/dashboard.html",
        datos=datos_kpi,
        ventas=ultimas_ventas,
        citas=ultimas_citas,
        cart_count=get_cart_count()
    )

@main.route("/admin/punto-venta", methods=["GET", "POST"])
def punto_venta():
    roles_permitidos = ["admin", "empleado", "cajero"]
    if session.get("user_rol") not in roles_permitidos:
        flash("No tienes permiso para acceder a la caja", "error")
        return redirect(url_for("main.admin_dashboard"))

    # venta física en sesión (independiente del carrito web)
    venta_actual = session.get("venta_fisica", [])

    # productos desde gadget.db (misma fuente real)
    productos_db = fetch_all_products(limit=None)
    total = sum(float(p.get("precio", 0)) * int(p.get("cantidad", 1)) for p in venta_actual)

    if request.method == "POST":
        codigo = (request.form.get("codigo_barras") or "").strip()
        accion = request.form.get("accion")

        # 1) ESCANEAR (usamos ID como código)
        if codigo:
            try:
                pid = int(codigo)
            except:
                pid = None

            if pid:
                prod = next((p for p in productos_db if int(p["id"]) == pid), None)
                if prod:
                    found = False
                    for item in venta_actual:
                        if int(item["id"]) == int(prod["id"]):
                            item["cantidad"] = int(item.get("cantidad", 1)) + 1
                            found = True
                            break
                    if not found:
                        nuevo = {
                            "id": int(prod["id"]),
                            "nombre": prod["nombre"],
                            "precio": float(prod["precio"] or 0),
                            "cantidad": 1,
                        }
                        venta_actual.append(nuevo)

                    session["venta_fisica"] = venta_actual
                else:
                    flash("Producto no encontrado", "error")

        # 2) FINALIZAR
        elif accion == "finalizar":
            session.pop("venta_fisica", None)
            flash("¡Venta cobrada con éxito!", "success")
            return redirect(url_for("main.punto_venta"))

        # 3) LIMPIAR
        elif accion == "limpiar":
            session.pop("venta_fisica", None)
            return redirect(url_for("main.punto_venta"))

        # 4) ELIMINAR ITEM
        elif accion == "eliminar_item":
            item_id = int(request.form.get("item_id"))
            venta_actual = [i for i in venta_actual if int(i["id"]) != item_id]
            session["venta_fisica"] = venta_actual
            return redirect(url_for("main.punto_venta"))

        total = sum(float(p.get("precio", 0)) * int(p.get("cantidad", 1)) for p in session.get("venta_fisica", []))

    return render_template(
        "admin/venta_fisica.html",
        venta=session.get("venta_fisica", []),
        total=total,
        productos_disponibles=productos_db,
        cart_count=get_cart_count()
    )

@main.route("/admin/usuarios", methods=["GET", "POST"])
def admin_usuarios():
    if session.get("user_rol") != "admin":
        return redirect(url_for("main.admin_dashboard"))

    conn = get_staff_conn()
    cur = conn.cursor()

    if request.method == "POST":
        u = request.form.get("nuevo_usuario", "").strip()
        p = request.form.get("nuevo_password", "")
        r = request.form.get("nuevo_rol", "").strip()

        try:
            # intentamos nombre_completo si existe
            try:
                cur.execute(
                    "INSERT INTO empleados (username, password_hash, rol, nombre_completo) VALUES (?, ?, ?, ?)",
                    (u, generate_password_hash(p), r, u.capitalize())
                )
            except:
                cur.execute(
                    "INSERT INTO empleados (username, password_hash, rol) VALUES (?, ?, ?)",
                    (u, generate_password_hash(p), r)
                )

            conn.commit()
            flash("Usuario creado", "success")
        except sqlite3.IntegrityError:
            flash("Error: Usuario duplicado", "error")

    cur.execute("SELECT * FROM empleados")
    usuarios = cur.fetchall()
    conn.close()

    return render_template("admin/usuarios_admin.html", usuarios=usuarios, cart_count=get_cart_count())

@main.route("/admin/productos")
def admin_productos():
    if "user_id" not in session or session.get("tipo_usuario") != "staff":
        return redirect(url_for("main.admin_login"))

    productos = fetch_all_products(limit=None)
    return render_template("admin/productos_admin.html", productos=productos, cart_count=get_cart_count())
