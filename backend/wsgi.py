"""Punto de entrada de la aplicación.

Desarrollo:
    python wsgi.py

Producción (dentro del contenedor Docker):
    gunicorn --bind 0.0.0.0:8000 wsgi:app
"""

import os

from dotenv import load_dotenv

# Carga variables desde .env (si existe) sin sobrescribir las ya definidas.
load_dotenv()

# Debe importarse después de load_dotenv() para leer las variables del .env.
from app import create_app  # noqa: E402  # pylint: disable=wrong-import-position

app = create_app()

if __name__ == "__main__":
    # Por defecto escucha solo en localhost: el modo debug de Flask NUNCA
    # debe exponerse a la red.
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )
