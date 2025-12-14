import os
import sqlite3
from flask import Flask, render_template, session
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ Base dir del proyecto (carpeta raíz)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # ✅ Ruta fija a gadget.db (sin depender de os.getcwd())
    db_path = os.path.join(base_dir, "database", "gadget.db")

    # ✅ Esto es CLAVE: routes.py usa current_app.config["DATABASE"]
    app.config["DATABASE"] = db_path

    # ✅ contador de carrito global para base.html
    @app.context_processor
    def inject_cart_count():
        carrito = session.get("carrito", [])
        cart_count = 0
        for i in carrito:
            try:
                cart_count += int(i.get("cantidad", 1))
            except:
                cart_count += 1
        return dict(cart_count=cart_count)

    def init_db():
        if not os.path.exists(db_path):
            print(f"➡ Creando base de datos SQLite en: {db_path}")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            init_sql_path = os.path.join(base_dir, "database", "init_db.sql")

            with open(init_sql_path, "r", encoding="utf-8") as f:
                cur.executescript(f.read())

            conn.commit()
            conn.close()
            print("✔ Base de datos creada exitosamente.")

    init_db()

    from .routes import main
    app.register_blueprint(main)

    # --------- Manejo de errores ---------
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errores/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("errores/500.html"), 500

    return app
