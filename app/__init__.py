import sqlite3
from flask import Flask
import os

def create_app():
    app = Flask(__name__)

    # --- ESTA LÍNEA ES LA QUE TE FALTABA PARA QUE EL LOGIN FUNCIONE ---
    app.secret_key = "clave_super_secreta_para_la_session" 
    # ------------------------------------------------------------------

    # Ruta a la base de datos
    db_path = os.path.join(os.getcwd(), "database", "la_casa.db")

    # Guardamos la ruta en config
    app.config["DATABASE"] = db_path

    # Función para inicializar DB si no existe
    def init_db():
        if not os.path.exists(db_path):
            print("➡ Creando base de datos SQLite...")
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Leer el archivo SQL
            with open("database/init_db.sql", "r", encoding="utf8") as f:
                cur.executescript(f.read())

            conn.commit()
            conn.close()
            print("✔ Base de datos creada exitosamente.")

    # Crear la base sólo si no existe
    init_db()

    # Registrar rutas
    from .routes import main
    app.register_blueprint(main)

    # Error handlers personalizados
    from flask import render_template

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errores/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('errores/500.html'), 500


    return app