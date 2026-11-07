"""Endpoints de la API v1.

Las rutas son delgadas: reciben la petición, delegan la validación en
``validators`` y la lógica en ``services``, y devuelven JSON.

Endpoints:
    GET  /api/v1/health              Estado del servicio.
    GET  /api/v1/passwords/options   Política y opciones admitidas.
    POST /api/v1/passwords/generate  Genera una contraseña aleatoria.
    POST /api/v1/passwords/strength  Evalúa la fortaleza de una contraseña.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, abort, jsonify, request

from app.errors import ValidationError
from app.extensions import limiter
from app.services import password_service
from app.validators import parse_generate_payload, parse_strength_payload

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# Límite más estricto para los endpoints que hacen trabajo.
_WRITE_RATE_LIMIT = "30/minute"


def _get_json_object() -> dict[str, Any]:
    """Obtiene el cuerpo JSON de la petición y exige que sea un objeto."""
    if not request.is_json:
        abort(415)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError({"body": "Debe ser un objeto JSON válido."})
    return payload


@api_bp.get("/health")
@limiter.exempt
def health() -> Response:
    """Permite a balanceadores y orquestadores (Docker) saber si la API vive."""
    return jsonify(status="ok")


@api_bp.get("/passwords/options")
def password_options() -> Response:
    return jsonify(password_service.get_password_policy())


@api_bp.post("/passwords/generate")
@limiter.limit(_WRITE_RATE_LIMIT)
def generate_password() -> Response:
    options = parse_generate_payload(_get_json_object())
    password = password_service.generate_password(options)
    strength = password_service.strength_of_generated(options)
    return jsonify(
        password=password,
        length=len(password),
        strength=strength.to_dict(),
    )


@api_bp.post("/passwords/strength")
@limiter.limit(_WRITE_RATE_LIMIT)
def password_strength() -> Response:
    password = parse_strength_payload(_get_json_object())
    result = password_service.evaluate_strength(password)
    return jsonify(result.to_dict())
