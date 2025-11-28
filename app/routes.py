from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import sqlite3

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/probar-producto')
def probar_producto():
    return render_template('citas.html')

@main.route('/empleados')
def empleados():
    return render_template('usuarios_admin.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@main.route('/carrito', methods=['GET', 'POST'])
def carrito():
    carrito = session.get('carrito', [])
    subtotal = sum(item['precio'] * item['cantidad'] for item in carrito)
    total = subtotal
    return render_template('carrito.html', carrito=carrito, subtotal=subtotal, total=total)

@main.route('/carrito/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_carrito(producto_id):
    carrito = session.get('carrito', [])
    carrito = [item for item in carrito if item['id'] != producto_id]
    session['carrito'] = carrito
    return redirect(url_for('main.carrito'))

@main.route('/carrito/pagar', methods=['POST'])
def pagar():
    return "<h1>¡Pago procesado! (Simulación)</h1>"

@main.route('/carrito/agregar/<int:producto_id>', methods=['POST'])
def agregar_carrito(producto_id):
    productos = [
        {
            "id": 1,
            "nombre": "iPhone 15 Pro Max 256GB",
            "marca": "Apple",
            "precio": 28999,
            "url_imagen": "/static/img/productos/iphone15.jpg",
            "categoria": "telefonos"
        },
        {
            "id": 2,
            "nombre": "Samsung Galaxy S24 Ultra",
            "marca": "Samsung",
            "precio": 26999,
            "url_imagen": "/static/img/productos/galaxywatch6.jpg",
            "categoria": "telefonos"
        },
        {
            "id": 3,
            "nombre": "iPad Pro 12.9\" M2",
            "marca": "Apple",
            "precio": 24999,
            "url_imagen": "/static/img/productos/ipad.jpg",
            "categoria": "tablets"
        },
        {
            "id": 4,
            "nombre": "MacBook Air M3",
            "marca": "Apple",
            "precio": 32999,
            "url_imagen": "/static/img/productos/macbook.jpg",
            "categoria": "laptops"
        },
        {
            "id": 5,
            "nombre": "Apple Watch Series 9",
            "marca": "Apple",
            "precio": 9999,
            "url_imagen": "/static/img/productos/watch.jpg",
            "categoria": "wearables"
        },
        {
            "id": 6,
            "nombre": "AirPods Pro 2da Gen",
            "marca": "Apple",
            "precio": 5999,
            "url_imagen": "/static/img/productos/airpods.jpg",
            "categoria": "accesorios"
        }
    ]
    producto = next((p for p in productos if p['id'] == producto_id), None)
    if producto:
        carrito = session.get('carrito', [])
        for item in carrito:
            if item['id'] == producto_id:
                if item['cantidad'] < 10:
                    item['cantidad'] += 1
                break
        else:
            producto_copy = producto.copy()
            producto_copy['cantidad'] = 1
            carrito.append(producto_copy)
        session['carrito'] = carrito
    return redirect(url_for('main.carrito'))

@main.route('/categoria/<categoria>', methods=['GET', 'POST'])
def productos_categoria(categoria):
    productos = [
    {
        "id": 1,
        "nombre": "iPhone 15 Pro Max 256GB",
        "marca": "Apple",
        "precio": 28999,
        "url_imagen": "/static/img/productos/iphone15.jpg",
        "categoria": "telefonos"
    },
    {
        "id": 2,
        "nombre": "Samsung Galaxy S24 Ultra",
        "marca": "Samsung",
        "precio": 26999,
        "url_imagen": "/static/img/productos/galaxywatch6.jpg",
        "categoria": "telefonos"
    },
    {
        "id": 3,
        "nombre": "iPad Pro 12.9\" M2",
        "marca": "Apple",
        "precio": 24999,
        "url_imagen": "/static/img/productos/ipad.jpg",
        "categoria": "tablets"
    },
    {
        "id": 4,
        "nombre": "MacBook Air M3",
        "marca": "Apple",
        "precio": 32999,
        "url_imagen": "/static/img/productos/macbookair.jpg",
        "categoria": "laptops"
    },
    {
        "id": 5,
        "nombre": "Audífonos Bluetooth Pro",
        "marca": "Xiaomi",
        "precio": 1999,
        "url_imagen": "/static/img/productos/AudífonosBluetoothPro.png",
        "categoria": "accesorios"
    },
    {
        "id": 6,
        "nombre": "Cargador Rápido 30W",
        "marca": "Samsung",
        "precio": 899,
        "url_imagen": "/static/img/productos/Cargador Rápido 30W.jpg",
        "categoria": "accesorios"
    },
    {
        "id": 7,
        "nombre": "Smartwatch Fit 5",
        "marca": "Samsung",
        "precio": 3999,
        "url_imagen": "/static/img/productos/Smartwatch Fit 5.jpg",
        "categoria": "wearables"
    },
    {
        "id": 8,
        "nombre": "Smartwatch Fit 5 (Edición Especial)",
        "marca": "Samsung",
        "precio": 4499,
        "url_imagen": "/static/img/productos/Smartwatch Fit 5.webp",
        "categoria": "wearables"
    },
    {
        "id": 9,
        "nombre": "Teclado Mecánico RGB",
        "marca": "Logitech",
        "precio": 1599,
        "url_imagen": "/static/img/productos/Teclado Mecánico RGB.jpg",
        "categoria": "accesorios"
    }
    ]
    # Toma la categoría del filtro si existe, si no usa la de la URL
    categoria_filtrada = request.args.get('categoria', categoria)
    productos_filtrados = [p for p in productos if p['categoria'] == categoria_filtrada]
    return render_template('producto_detalle.html', productos=productos_filtrados, categoria=categoria_filtrada)

@main.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@main.route('/carrito/actualizar/<int:producto_id>', methods=['POST'])
def actualizar_carrito(producto_id):
    accion = request.form.get('accion')
    carrito = session.get('carrito', [])
    conn = sqlite3.connect(current_app.config['DATABASE'])
    cur = conn.cursor()
    cur.execute("SELECT stock FROM inventario WHERE producto_id = ?", (producto_id,))
    result = cur.fetchone()
    stock_disponible = result[0] if result else 0
    conn.close()
    for item in carrito:
        if item['id'] == producto_id:
            if accion == 'sumar' and item['cantidad'] < min(10, stock_disponible):
                item['cantidad'] += 1
            elif accion == 'restar' and item['cantidad'] > 1:
                item['cantidad'] -= 1
    session['carrito'] = carrito
    return redirect(url_for('main.carrito'))