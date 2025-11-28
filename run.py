from app import create_app

# Crea la aplicación usando la fábrica
app = create_app()

if __name__ == '__main__':
    # Ejecuta el servidor en modo debug
    app.run(debug=True, port=5000)