"""Pruebas MODULARES del manejo de errores: app/errors.py

El módulo se monta en una app Flask MÍNIMA con rutas de prueba que provocan
cada tipo de error. Así se verifica el módulo completo, independiente de las
rutas, validadores y servicios de PassForge.
"""

import logging

import pytest
from flask import Flask, abort

from app.errors import ValidationError, register_error_handlers

pytestmark = pytest.mark.module


@pytest.fixture
def error_client():
    app = Flask(__name__)
    register_error_handlers(app)

    @app.get("/validation")
    def validation_error():
        raise ValidationError({"campo": "Mensaje de error."})

    @app.get("/abort/<int:status>")
    def abort_with(status):
        abort(status)

    @app.post("/solo-post")
    def only_post():
        return "ok"

    @app.get("/boom")
    def unexpected_error():
        raise RuntimeError("detalle interno secreto")

    return app.test_client()


class TestErrorResponses:
    def test_validation_error_returns_400_with_details(self, error_client):
        # Act
        response = error_client.get("/validation")

        # Assert
        assert response.status_code == 400
        assert response.get_json() == {
            "error": {
                "code": "validation_error",
                "message": "Datos de entrada inválidos.",
                "details": {"campo": "Mensaje de error."},
            }
        }

    @pytest.mark.parametrize(
        ("status", "code"),
        [
            (400, "bad_request"),
            (404, "not_found"),
            (413, "request_entity_too_large"),
            (415, "unsupported_media_type"),
            (429, "too_many_requests"),
        ],
    )
    def test_http_errors_are_returned_as_json(self, error_client, status, code):
        # Act
        response = error_client.get(f"/abort/{status}")

        # Assert
        assert response.status_code == status
        assert response.is_json
        assert response.get_json()["error"]["code"] == code
        assert response.get_json()["error"]["message"]

    def test_unlisted_http_error_uses_its_standard_description(self, error_client):
        # 418 no tiene mensaje propio: se usa la descripción estándar de HTTP
        response = error_client.get("/abort/418")

        assert response.status_code == 418
        assert response.get_json()["error"]["message"]

    def test_unknown_route_returns_json_404(self, error_client):
        response = error_client.get("/no-existe")

        assert response.status_code == 404
        assert response.get_json()["error"]["code"] == "not_found"

    def test_method_not_allowed_keeps_the_allow_header(self, error_client):
        response = error_client.get("/solo-post")

        assert response.status_code == 405
        assert "POST" in response.headers["Allow"]
        assert response.headers["Content-Type"] == "application/json"


class TestUnexpectedErrors:
    def test_return_500_without_revealing_internal_details(self, error_client):
        # Act
        response = error_client.get("/boom")

        # Assert
        assert response.status_code == 500
        assert response.get_json() == {
            "error": {
                "code": "internal_server_error",
                "message": "Ocurrió un error interno en el servidor.",
            }
        }
        assert "secreto" not in response.get_data(as_text=True)

    def test_are_logged_for_developers(self, error_client, caplog):
        # Act
        with caplog.at_level(logging.ERROR):
            error_client.get("/boom")

        # Assert: el detalle va a los logs del servidor, no al cliente
        assert "Error no controlado: RuntimeError" in caplog.text
