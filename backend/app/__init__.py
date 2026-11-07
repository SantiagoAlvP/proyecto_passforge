"""Backend de PassForge.

Expone ``create_app``, la *application factory* de Flask. Una factory permite
crear instancias aisladas de la app con configuraciones distintas (por
ejemplo, una por cada prueba automatizada).
"""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.api import api_bp
from app.config import get_config
from app.errors import register_error_handlers
from app.extensions import cors, limiter
from app.security import register_security_headers


def create_app(
    env_name: str | None = None, overrides: dict[str, Any] | None = None
) -> Flask:
    """Crea y configura una instancia de la aplicación Flask.

    Args:
        env_name: ``development``, ``testing`` o ``production``. Si es
            ``None`` se usa la variable de entorno ``APP_ENV``.
        overrides: valores de configuración que reemplazan a los del entorno
            (útil en pruebas).
    """
    app = Flask(__name__)
    app.config.from_object(get_config(env_name))
    if overrides:
        app.config.update(overrides)
    # Respeta el orden de las claves y muestra tildes/ñ sin escapar.
    app.json.sort_keys = False  # type: ignore[attr-defined]
    app.json.ensure_ascii = False  # type: ignore[attr-defined]

    _configure_logging(app)

    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # type: ignore[method-assign]

    # CORS: solo los orígenes configurados (el frontend) pueden llamar a la API.
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        supports_credentials=False,
        max_age=600,
    )
    limiter.init_app(app)

    app.register_blueprint(api_bp)
    register_error_handlers(app)
    register_security_headers(app)
    return app


def _configure_logging(app: Flask) -> None:
    level = app.config["LOG_LEVEL"]
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger.setLevel(level)
