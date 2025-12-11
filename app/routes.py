from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash, json
import sqlite3
import os
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

main = Blueprint('main', __name__)

# --- FUNCIÓN AUXILIAR PARA CARGAR PRODUCTOS JSON ---
def cargar_productos_json():
    try:
        # Ruta absoluta al archivo JSON
        json_path = os.path.join(current_app.root_path, 'static', 'productos.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            productos = json.load(f)
            # Aseguramos que tengan stock para que no falle la vista
            for p in productos:
                if 'stock' not in p:
                    p['stock'] = 10 
            return productos
    except Exception as e:
        print(f"Error cargando JSON: {e}")
        return []

# ==========================================
# RUTAS PÚBLICAS (CLIENTES)
# ==========================================

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/probar-producto')
def probar_producto():
    return render_template('citas.html')

@main.route('/empleados')
def empleados():
    # Si ya está logueado, lo mandamos a su lugar correspondiente
    if 'user_id' in session and session.get('tipo_usuario') == 'staff':
        rol = session.get('user_rol')
        if rol == 'empleado' or rol == 'cajero':
            return redirect(url_for('main.punto_venta'))
        return redirect(url_for('main.admin_dashboard'))
    
    # Si no, al login
    return redirect(url_for('main.admin_login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

# ==========================================
# RUTAS DE CARRITO (CLIENTES WEB)
# ==========================================

@main.route('/carrito', methods=['GET', 'POST'])
def carrito():
    carrito = session.get('carrito', [])
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    total = subtotal
    return render_template('carrito.html', carrito=carrito, subtotal=subtotal, total=total)

@main.route('/carrito/agregar/<int:producto_id>', methods=['POST'])
def agregar_carrito(producto_id):
    productos = cargar_productos_json()
    producto = next((p for p in productos if p['id'] == producto_id), None)
    if producto:
        carrito = session.get('carrito', [])
        found = False
        for item in carrito:
            if item['id'] == producto_id:
                if item['cantidad'] < 10:
                    item['cantidad'] += 1
                found = True
                break
        if not found:
            producto_copy = producto.copy()
            producto_copy['cantidad'] = 1
            carrito.append(producto_copy)
        session['carrito'] = carrito
    return redirect(url_for('main.carrito'))

@main.route('/carrito/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_carrito(producto_id):
    carrito = [item for item in session.get('carrito', []) if item['id'] != producto_id]
    session['carrito'] = carrito
    return redirect(url_for('main.carrito'))

@main.route('/carrito/actualizar/<int:producto_id>', methods=['POST'])
def actualizar_carrito(producto_id):
    accion = request.form.get('accion')
    carrito = session.get('carrito', [])
    for item in carrito:
        if item['id'] == producto_id:
            if accion == 'sumar' and item['cantidad'] < 10:
                item['cantidad'] += 1
            elif accion == 'restar' and item['cantidad'] > 1:
                item['cantidad'] -= 1
    session['carrito'] = carrito
    return redirect(url_for('main.carrito'))

@main.route('/carrito/pagar', methods=['POST'])
def pagar():
    return "<h1>¡Pago procesado! (Simulación)</h1>"

@main.route('/categoria/<categoria>', methods=['GET', 'POST'])
def productos_categoria(categoria):
    productos = cargar_productos_json()
    filtrados = [p for p in productos if p['categoria'] == categoria]
    return render_template('producto_detalle.html', productos=filtrados, categoria=categoria)


# ==========================================
# RUTAS PRIVADAS (STAFF / ADMIN / CAJEROS)
# ==========================================

@main.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['contraseña']
        
        db_path = os.path.join(os.getcwd(), 'database', 'empleados.db')
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM empleados WHERE username = ?", (usuario,))
            user = cur.fetchone()
            conn.close()

            if user and check_password_hash(user['password_hash'], password):
                # Guardar datos en sesión
                session['user_id'] = user['id']
                session['username'] = user['username']
                # Intentamos obtener nombre real, si no existe usamos el username
                session['nombre_completo'] = user['nombre_completo'] if 'nombre_completo' in user.keys() else user['username']
                session['user_rol'] = user['rol']
                session['tipo_usuario'] = 'staff'
                session['fecha_hoy'] = datetime.now().strftime("%d/%m/%Y")
                
                # --- AQUÍ ESTÁ LA LÓGICA QUE PEDISTE ---
                # Si es empleado o cajero -> Va directo a la caja
                if user['rol'] == 'empleado' or user['rol'] == 'cajero':
                    return redirect(url_for('main.punto_venta'))
                
                # Si es admin o gerente -> Va al dashboard
                else:
                    return redirect(url_for('main.admin_dashboard'))
                # ---------------------------------------
            else:
                flash("Credenciales incorrectas", "error")
                
        except Exception as e:
            print(f"Error Login: {e}")
            flash("Error de conexión", "error")

    return render_template('admin/login.html')

@main.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@main.route('/admin/dashboard')
def admin_dashboard():
    # Protección
    if 'user_id' not in session or session.get('tipo_usuario') != 'staff':
        return redirect(url_for('main.admin_login'))
    
    # Datos simulados para KPIs
    datos_kpi = {
        "ventas_dia": 45230,
        "citas_hoy": 8,
        "stock_bajo": 5,
        "empleado_mes": "Leo Cruz",
        "fecha_hoy": datetime.now().strftime("%d/%m/%Y")
    }
    
    # Tablas simuladas
    ultimas_ventas = [
        {"fecha": "11/12/2025", "vendedor": "Cajero 1", "producto": "iPhone 15", "total": 28999},
        {"fecha": "11/12/2025", "vendedor": "Leo Cruz", "producto": "AirPods Pro", "total": 5999}
    ]
    ultimas_citas = [
        {"hora": "10:00 AM", "cliente": "Ana López", "producto": "MacBook Air", "estado": "Confirmada"},
        {"hora": "12:30 PM", "cliente": "Carlos Ruiz", "producto": "Galaxy S24", "estado": "Pendiente"}
    ]

    return render_template('admin/dashboard.html', 
                           datos=datos_kpi, 
                           ventas=ultimas_ventas, 
                           citas=ultimas_citas)

# --- PUNTO DE VENTA (ESCÁNER & CÁMARA) ---
@main.route('/admin/punto-venta', methods=['GET', 'POST'])
def punto_venta():
    # Solo empleados, cajeros y admins pueden vender
    roles_permitidos = ['admin', 'empleado', 'cajero']
    if session.get('user_rol') not in roles_permitidos:
        flash("No tienes permiso para acceder a la caja", "error")
        return redirect(url_for('main.admin_dashboard'))

    # Carrito de venta física en sesión
    venta_actual = session.get('venta_fisica', [])
    productos_db = cargar_productos_json()
    total = sum(p['precio'] * p['cantidad'] for p in venta_actual)

    if request.method == 'POST':
        codigo = request.form.get('codigo_barras')
        accion = request.form.get('accion')

        # 1. ESCANEO (Por input o cámara)
        if codigo:
            # Buscamos por ID simulando código de barras
            prod = next((p for p in productos_db if str(p['id']) == codigo), None)
            
            if prod:
                found = False
                for item in venta_actual:
                    if item['id'] == prod['id']:
                        item['cantidad'] += 1
                        found = True
                        break
                if not found:
                    nuevo = prod.copy()
                    nuevo['cantidad'] = 1
                    venta_actual.append(nuevo)
                
                session['venta_fisica'] = venta_actual
                # flash opcional
            else:
                flash("Producto no encontrado", "error")
        
        # 2. FINALIZAR VENTA
        elif accion == 'finalizar':
            # Aquí guardarías en DB real en la etapa 3
            session.pop('venta_fisica', None)
            flash("¡Venta cobrada con éxito!", "success")
            return redirect(url_for('main.punto_venta'))
            
        # 3. CANCELAR VENTA
        elif accion == 'limpiar':
            session.pop('venta_fisica', None)
            return redirect(url_for('main.punto_venta'))
            
        # 4. ELIMINAR UN ITEM
        elif accion == 'eliminar_item':
            item_id = int(request.form.get('item_id'))
            venta_actual = [i for i in venta_actual if i['id'] != item_id]
            session['venta_fisica'] = venta_actual
            return redirect(url_for('main.punto_venta'))

    # Pasamos productos_disponibles para que el JS del simulador sepa qué elegir
    return render_template('admin/venta_fisica.html', 
                           venta=venta_actual, 
                           total=total, 
                           productos_disponibles=productos_db)

# --- GESTIÓN DE USUARIOS ---
@main.route('/admin/usuarios', methods=['GET', 'POST'])
def admin_usuarios():
    if session.get('user_rol') != 'admin':
        return redirect(url_for('main.admin_dashboard'))

    db_path = os.path.join(os.getcwd(), 'database', 'empleados.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'POST':
        u = request.form['nuevo_usuario']
        p = request.form['nuevo_password']
        r = request.form['nuevo_rol']
        
        try:
            # Intentamos guardar nombre completo si la columna existe, si no solo lo básico
            try:
                cur.execute("INSERT INTO empleados (username, password_hash, rol, nombre_completo) VALUES (?, ?, ?, ?)",
                            (u, generate_password_hash(p), r, u.capitalize()))
            except:
                # Fallback por si la DB vieja no tiene la columna nombre_completo
                cur.execute("INSERT INTO empleados (username, password_hash, rol) VALUES (?, ?, ?)",
                            (u, generate_password_hash(p), r))
            
            conn.commit()
            flash("Usuario creado", "success")
        except sqlite3.IntegrityError:
            flash("Error: Usuario duplicado", "error")

    cur.execute("SELECT * FROM empleados")
    usuarios = cur.fetchall()
    conn.close()
    
    return render_template('admin/usuarios_admin.html', usuarios=usuarios)

# --- INVENTARIO ---
@main.route('/admin/productos')
def admin_productos():
    if 'user_id' not in session: return redirect(url_for('main.admin_login'))
    productos = cargar_productos_json()
    return render_template('admin/productos_admin.html', productos=productos)