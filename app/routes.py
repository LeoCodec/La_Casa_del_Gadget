from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash
import sqlite3

main = Blueprint("main", __name__)

# ---------------------------
# Helpers DB
# ---------------------------
def get_conn():
    conn = sqlite3.connect(current_app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn

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

# ---------------------------
# Routes base
# ---------------------------
@main.route("/")
def index():
    productos_destacados = fetch_all_products(limit=8)
    return render_template("index.html", productos_destacados=productos_destacados)

@main.route("/probar-producto")
def probar_producto():
    return render_template("citas.html")

@main.route("/empleados")
def empleados():
    return render_template("usuarios_admin.html")

@main.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")

@main.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")

# ---------------------------
# ✅ Productos + filtros
# ---------------------------
@main.route("/productos")
def productos_listado():
    # Tipos "principales" (los que NO deben caer en accesorios)
    tipos_principales = ["Smartphone", "Laptop", "Tablet"]

    # Leer filtros (checkbox => listas)
    categorias = request.args.getlist("categoria")  # e.g. ["telefonos","accesorios"]
    marcas = request.args.getlist("marca")          # e.g. ["Apple","Samsung"]
    q = (request.args.get("q") or "").strip()
    precio_max = request.args.get("precio_max")

    try:
        precio_max_num = float(precio_max) if precio_max not in (None, "") else None
    except ValueError:
        precio_max_num = None

    where = ["disponible = 1"]
    params = []

    # ----- Categorías -----
    # telefonos  -> tipo = Smartphone
    # laptops    -> tipo = Laptop
    # tablets    -> tipo = Tablet
    # accesorios -> tipo NOT IN (Smartphone,Laptop,Tablet,Wearable)  (TODO lo demás)
    tipos_in = []
    accesorios_activado = False

    for cat in categorias:
        if cat == "telefonos":
            tipos_in.append("Smartphone")
        elif cat == "laptops":
            tipos_in.append("Laptop")
        elif cat == "tablets":
            tipos_in.append("Tablet")
        elif cat == "accesorios":
            accesorios_activado = True

    tipos_in = sorted(set(tipos_in))

    # Si el usuario selecciona accesorios, filtramos "todo lo demás".
    # Si además selecciona teléfonos (por ejemplo), debe ser OR entre:
    #   tipo IN (...)  OR  tipo NOT IN (principales)
    # Para lograrlo en SQL sin complicarlo, armamos un bloque OR.
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
    # Si no seleccionó nada => no se agrega filtro => muestra TODO

    # ----- Marca -----
    if marcas:
        where.append(f"marca IN ({','.join(['?']*len(marcas))})")
        params.extend(marcas)

    # ----- Búsqueda -----
    if q:
        where.append("(nombre LIKE ? OR marca LIKE ? OR tipo LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    # ----- Precio -----
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
        "max_precio_real": max(fetch_max_precio(), 50000)
    }

    filtros = {
        "categorias": categorias,
        "marcas": marcas,
        "q": q,
        "precio_max": precio_max_num if precio_max_num is not None else ui_data["max_precio_real"]
    }

    return render_template("producto_detalle.html", productos=productos, filtros=filtros, ui_data=ui_data)

# ---------------------------
# ✅ Carrito (arreglado)
# ---------------------------
@main.route("/carrito", methods=["GET"])
def carrito():
    carrito = session.get("carrito", [])

    # asegurar tipos correctos
    for item in carrito:
        item["precio"] = float(item.get("precio", 0))
        item["cantidad"] = int(item.get("cantidad", 1))

    subtotal = sum(item["precio"] * item["cantidad"] for item in carrito)
    total = subtotal

    return render_template("carrito.html", carrito=carrito, subtotal=subtotal, total=total)

@main.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    producto = get_producto_basico(producto_id)
    if not producto:
        return redirect(url_for("main.productos_listado"))

    stock_total = get_stock_total(producto_id)
    if stock_total <= 0:
        # si quieres ver mensajes, usa flash() y muéstralo en el template
        # flash("Sin stock disponible para este producto.", "warning")
        return redirect(url_for("main.productos_listado"))

    carrito = session.get("carrito", [])

    # normalizar
    for item in carrito:
        item["cantidad"] = int(item.get("cantidad", 1))
        item["precio"] = float(item.get("precio", 0))

    # si ya existe, aumentar si hay stock y límite 10
    for item in carrito:
        if item["id"] == producto_id:
            nuevo = item["cantidad"] + 1
            if nuevo <= min(10, stock_total):
                item["cantidad"] = nuevo
            session["carrito"] = carrito
            return redirect(url_for("main.carrito"))

    # si no existe, agregar con cantidad 1
    producto_item = {
        "id": int(producto["id"]),
        "nombre": producto["nombre"],
        "marca": producto["marca"],
        "tipo": producto["tipo"],
        "precio": float(producto["precio"] or 0),
        "url_imagen": producto.get("url_imagen"),
        "cantidad": 1,
    }
    carrito.append(producto_item)
    session["carrito"] = carrito
    return redirect(url_for("main.carrito"))

@main.route("/carrito/actualizar/<int:producto_id>", methods=["POST"])
def actualizar_carrito(producto_id):
    accion = request.form.get("accion")  # "sumar" o "restar"
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
    # Simulación
    # Aquí podrías crear una venta en la tabla ventas + detalle_venta
    session["carrito"] = []
    return "<h1>¡Pago procesado! (Simulación)</h1>"
