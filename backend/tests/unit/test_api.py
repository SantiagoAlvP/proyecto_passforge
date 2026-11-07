"""Pruebas de los endpoints de la API con el cliente de prueba de Flask.

No se levanta un servidor real: ``client`` envía las peticiones directamente
a la app, así que las pruebas son rápidas y aisladas.
"""

from __future__ import annotations

from app.services import password_service as svc

API = "/api/v1"


# --------------------------------------------------------------------------- #
# GET /health
# --------------------------------------------------------------------------- #
def test_health_returns_ok(client):
    # Act
    response = client.get(f"{API}/health")

    # Assert
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_responses_include_security_headers(client):
    # Act
    response = client.get(f"{API}/health")

    # Assert
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in response.headers


# --------------------------------------------------------------------------- #
# GET /passwords/options
# --------------------------------------------------------------------------- #
def test_options_returns_policy(client):
    # Act
    response = client.get(f"{API}/passwords/options")

    # Assert
    assert response.status_code == 200
    assert response.get_json() == svc.get_password_policy()


# --------------------------------------------------------------------------- #
# POST /passwords/generate
# --------------------------------------------------------------------------- #
def test_generate_returns_password_with_requested_options(client):
    # Arrange
    payload = {"length": 24, "include_symbols": False}

    # Act
    response = client.post(f"{API}/passwords/generate", json=payload)

    # Assert
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["password"]) == 24 == body["length"]
    assert not set(body["password"]) & set(svc.SYMBOLS)
    assert set(body["strength"]) == {"score", "label", "entropy_bits", "feedback"}


def test_generate_with_empty_body_uses_defaults(client):
    response = client.post(f"{API}/passwords/generate", json={})

    assert response.status_code == 200
    assert response.get_json()["length"] == svc.DEFAULT_LENGTH


def test_generate_invalid_length_returns_400(client):
    # Act
    response = client.post(f"{API}/passwords/generate", json={"length": 3})

    # Assert
    assert response.status_code == 400
    error = response.get_json()["error"]
    assert error["code"] == "validation_error"
    assert "length" in error["details"]


def test_generate_without_json_content_type_returns_415(client):
    response = client.post(f"{API}/passwords/generate", data="length=16")

    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "unsupported_media_type"


def test_generate_with_json_array_returns_400(client):
    response = client.post(f"{API}/passwords/generate", json=[1, 2, 3])

    assert response.status_code == 400
    assert "body" in response.get_json()["error"]["details"]


# --------------------------------------------------------------------------- #
# POST /passwords/strength
# --------------------------------------------------------------------------- #
def test_strength_evaluates_password(client):
    # Act
    response = client.post(f"{API}/passwords/strength", json={"password": "123456"})

    # Assert
    assert response.status_code == 200
    body = response.get_json()
    assert body["score"] == 0
    assert body["label"] == "muy débil"


def test_strength_missing_password_returns_400(client):
    response = client.post(f"{API}/passwords/strength", json={})

    assert response.status_code == 400
    assert "password" in response.get_json()["error"]["details"]


# --------------------------------------------------------------------------- #
# Manejo de errores genérico
# --------------------------------------------------------------------------- #
def test_unknown_route_returns_json_404(client):
    response = client.get(f"{API}/no-existe")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_wrong_method_returns_405_with_allow_header(client):
    response = client.delete(f"{API}/health")

    assert response.status_code == 405
    assert "GET" in response.headers["Allow"]


def test_body_too_large_returns_413(client):
    response = client.post(
        f"{API}/passwords/strength", json={"password": "a" * 5000}
    )

    assert response.status_code == 413


def test_unexpected_error_returns_generic_500(app, client, monkeypatch):
    # Arrange: forzamos un fallo interno en el servicio.
    def boom():
        raise RuntimeError("detalle interno secreto")

    monkeypatch.setattr(svc, "get_password_policy", boom)

    # Act
    response = client.get(f"{API}/passwords/options")

    # Assert: no se filtra el detalle interno al cliente.
    assert response.status_code == 500
    assert "secreto" not in response.get_data(as_text=True)
    assert response.get_json()["error"]["code"] == "internal_server_error"


def test_cors_allows_frontend_origin(client):
    response = client.get(
        f"{API}/health", headers={"Origin": "http://127.0.0.1:5500"}
    )

    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5500"


def test_cors_rejects_unknown_origin(client):
    response = client.get(f"{API}/health", headers={"Origin": "http://evil.com"})

    assert "Access-Control-Allow-Origin" not in response.headers
