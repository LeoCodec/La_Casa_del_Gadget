import sqlite3
from werkzeug.security import generate_password_hash
import os

def init_empleados_db():
    # Asegurar ruta correcta
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'empleados.db')
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Borrar tabla anterior si existe para empezar limpio
    cur.execute('DROP TABLE IF EXISTS empleados')

    # Crear tabla de empleados con los nuevos roles
    cur.execute('''
    CREATE TABLE empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        nombre_completo TEXT,
        rol TEXT NOT NULL, -- 'admin', 'gerente', 'empleado', 'visitante'
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # --- LISTA DE USUARIOS REALES ---
    usuarios = [
        # (Usuario, Contraseña, Nombre Real, Rol)
        ('admin', 'admin123', 'Super Admin', 'admin'),
        ('leocruz', 'leo123', 'Leo Cruz', 'admin'), # Tu usuario admin
        ('gerente', 'gerente123', 'Gerente General', 'gerente'),
        ('cajero1', 'caja1', 'Empleado Mostrador 1', 'empleado'), # El que usa el escáner
        ('samsung_rep', 'sam123', 'Rep. Samsung', 'visitante'), # Marca externa
    ]

    print("--- Creando usuarios y roles ---")
    for user, pwd, nombre, rol in usuarios:
        pwd_hash = generate_password_hash(pwd)
        try:
            cur.execute('''
                INSERT INTO empleados (username, password_hash, nombre_completo, rol) 
                VALUES (?, ?, ?, ?)
            ''', (user, pwd_hash, nombre, rol))
            print(f"✔ Usuario '{user}' ({rol}) creado.")
        except sqlite3.IntegrityError:
            print(f"⚠ El usuario '{user}' ya existe.")

    conn.commit()
    conn.close()
    print("\n¡Base de datos 'empleados.db' actualizada con nuevos roles!")

if __name__ == '__main__':
    init_empleados_db()