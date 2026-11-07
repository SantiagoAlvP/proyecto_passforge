"""Punto de entrada de la aplicación.

Desarrollo:
    python wsgi.py

Producción (más adelante, dentro de Docker):
    gunicorn --bind 0.0.0.0:8000 wsgi:app
"""

import os

from dotenv import load_dotenv

# Carga variables desde .env (si existe) sin sobrescribir las ya definidas.
load_dotenv()

from app import create_app  # noqa: E402  (debe ir después de load_dotenv)

app = create_app()

if __name__ == "__main__":
    # Por defecto escucha solo en localhost: el modo debug de Flask NUNCA
    # debe exponerse a la red.
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
