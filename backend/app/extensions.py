"""Instancias de extensiones de Flask.

Se crean aquí sin app y se enlazan en ``create_app`` con ``init_app``.
Así se evitan importaciones circulares y cada app de prueba es independiente.
"""

from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

cors = CORS()

# Limita peticiones por IP para mitigar abusos y ataques de fuerza bruta.
limiter = Limiter(key_func=get_remote_address)
