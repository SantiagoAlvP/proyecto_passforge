"""Pruebas UNITARIAS de app/errors.py

Prueban la excepción ValidationError y la función error_response por
separado. (El comportamiento de los manejadores de errores registrados en una
app se prueba en tests/module/test_errors_module.py).
"""

import pytest
from flask import Flask

from app.errors import ValidationError, error_response

pytestmark = pytest.mark.unit


class TestValidationError:
    def test_keeps_details_and_default_message(self):
        # Act
        error = ValidationError({"length": "Debe ser un número entero."})

        # Assert
        assert error.details == {"length": "Debe ser un número entero."}
        assert error.message == "Datos de entrada inválidos."
        assert str(error) == "Datos de entrada inválidos."

    def test_accepts_a_custom_message(self):
        error = ValidationError({}, message="Mensaje propio.")

        assert error.message == "Mensaje propio."


class TestErrorResponse:
    @pytest.fixture
    def app_context(self):
        # jsonify() necesita un contexto de aplicación de Flask.
        with Flask(__name__).app_context():
            yield

    def test_builds_body_without_details(self, app_context):
        # Act
        response, status = error_response(404, "not_found", "No existe.")

        # Assert
        assert status == 404
        assert response.get_json() == {"error": {"code": "not_found", "message": "No existe."}}

    def test_includes_details_when_given(self, app_context):
        response, status = error_response(400, "validation_error", "Inválido.", {"campo": "malo"})

        assert status == 400
        assert response.get_json()["error"]["details"] == {"campo": "malo"}
