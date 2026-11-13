"""Pruebas MODULARES de las cabeceras de seguridad: app/security.py

El módulo se registra en una app Flask MÍNIMA (no en PassForge) para
verificar que añade sus cabeceras a cualquier respuesta, por sí solo.
"""

import pytest
from flask import Flask

from app.security import register_security_headers

pytestmark = pytest.mark.module

EXPECTED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
}


def make_client(hsts_enabled=False):
    app = Flask(__name__)
    app.config["HSTS_ENABLED"] = hsts_enabled
    register_security_headers(app)

    @app.get("/")
    def index():
        return {"ok": True}

    @app.get("/cacheable")
    def cacheable():
        # Una ruta que, por error, intenta permitir la caché.
        return {"ok": True}, 200, {"Cache-Control": "public, max-age=3600"}

    return app.test_client()


class TestSecurityHeaders:
    @pytest.mark.parametrize(("path", "status"), [("/", 200), ("/no-existe", 404)])
    def test_are_added_to_every_response(self, path, status):
        # Act
        response = make_client().get(path)

        # Assert: también en las respuestas de error
        assert response.status_code == status
        for name, value in EXPECTED_HEADERS.items():
            assert response.headers[name] == value

    def test_overwrite_unsafe_values_set_by_a_route(self):
        response = make_client().get("/cacheable")

        assert response.headers["Cache-Control"] == "no-store"

    def test_hsts_is_not_sent_when_disabled(self):
        response = make_client(hsts_enabled=False).get("/")

        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_is_sent_when_enabled(self):
        response = make_client(hsts_enabled=True).get("/")

        assert response.headers["Strict-Transport-Security"] == (
            "max-age=31536000; includeSubDomains"
        )
