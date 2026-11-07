"""Manejo centralizado de errores.

Todas las respuestas de error tienen el mismo formato JSON::

    {"error": {"code": "...", "message": "...", "details": {...}}}

Nunca se envía al cliente el detalle interno de una excepción (stack trace):
eso se registra en los logs del servidor.
"""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException

_HTTP_MESSAGES = {
    400: "La solicitud no es válida.",
    404: "El recurso solicitado no existe.",
    405: "Método HTTP no permitido para este recurso.",
    413: "El cuerpo de la solicitud es demasiado grande.",
    415: "El contenido debe enviarse como JSON (Content-Type: application/json).",
    429: "Demasiadas solicitudes. Intenta de nuevo en unos momentos.",
    500: "Ocurrió un error interno en el servidor.",
}


class ValidationError(Exception):
    """Error de validación de datos de entrada (HTTP 400)."""

    def __init__(
        self, details: dict[str, str], message: str = "Datos de entrada inválidos."
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


def error_response(
    status: int, code: str, message: str, details: dict[str, Any] | None = None
) -> tuple[Response, int]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return jsonify(error=body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> tuple[Response, int]:
        return error_response(400, "validation_error", error.message, error.details)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException) -> tuple[Response, int]:
        status = error.code or 500
        code = (error.name or "error").lower().replace(" ", "_")
        message = _HTTP_MESSAGES.get(status, error.description or "Error.")
        response, status = error_response(status, code, message)
        # Conserva cabeceras útiles de la excepción (p. ej. "Allow" en un 405).
        for name, value in error.get_headers():
            if name.lower() != "content-type":
                response.headers[name] = value
        return response, status

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
        app.logger.exception("Error no controlado: %s", type(error).__name__)
        return error_response(500, "internal_server_error", _HTTP_MESSAGES[500])
