"""Pruebas UNITARIAS de las rutas: app/api/routes.py

Se prueba SOLO la capa HTTP. El servicio de contraseñas se reemplaza por
dobles de prueba (``monkeypatch``), así se verifica que cada ruta:
  - entrega al servicio los datos correctos,
  - arma la respuesta JSON con lo que el servicio devuelve, y
  - NO llama al servicio cuando la petición es inválida.

(Las pruebas con el servicio real están en tests/integration/).
"""

import pytest

from app.services import password_service
from app.services.password_service import PasswordOptions, StrengthResult

pytestmark = pytest.mark.unit

API = "/api/v1"
FAKE_STRENGTH = StrengthResult(score=4, label="muy fuerte", entropy_bits=200.0)


@pytest.fixture
def service_calls(monkeypatch):
    """Reemplaza el servicio por dobles que registran con qué se les llamó."""
    calls = {"generate": [], "evaluate": []}

    def fake_generate(options):
        calls["generate"].append(options)
        return "X" * options.length

    def fake_evaluate(password):
        calls["evaluate"].append(password)
        return StrengthResult(score=1, label="débil", entropy_bits=30.0, feedback=["consejo"])

    monkeypatch.setattr(password_service, "generate_password", fake_generate)
    monkeypatch.setattr(password_service, "strength_of_generated", lambda options: FAKE_STRENGTH)
    monkeypatch.setattr(password_service, "evaluate_strength", fake_evaluate)
    return calls


class TestHealthRoute:
    def test_returns_ok(self, client):
        response = client.get(f"{API}/health")

        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}


class TestOptionsRoute:
    def test_returns_the_policy_given_by_the_service(self, client, monkeypatch):
        # Arrange
        monkeypatch.setattr(password_service, "get_password_policy", lambda: {"fake": "policy"})

        # Act
        response = client.get(f"{API}/passwords/options")

        # Assert
        assert response.status_code == 200
        assert response.get_json() == {"fake": "policy"}


class TestGenerateRoute:
    def test_passes_the_validated_options_to_the_service(self, client, service_calls):
        # Act
        client.post(f"{API}/passwords/generate", json={"length": 20, "include_symbols": False})

        # Assert
        assert service_calls["generate"] == [PasswordOptions(length=20, include_symbols=False)]

    def test_builds_the_response_with_the_service_results(self, client, service_calls):
        # Act
        response = client.post(f"{API}/passwords/generate", json={"length": 10})

        # Assert
        assert response.status_code == 200
        assert response.get_json() == {
            "password": "XXXXXXXXXX",
            "length": 10,
            "strength": {
                "score": 4,
                "label": "muy fuerte",
                "entropy_bits": 200.0,
                "feedback": [],
            },
        }

    def test_service_is_not_called_when_validation_fails(self, client, service_calls):
        # Act
        response = client.post(f"{API}/passwords/generate", json={"length": 1})

        # Assert
        assert response.status_code == 400
        assert service_calls["generate"] == []

    def test_rejects_a_body_that_is_not_json(self, client, service_calls):
        response = client.post(f"{API}/passwords/generate", data={"length": "16"})

        assert response.status_code == 415
        assert service_calls["generate"] == []

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"json": [1, 2, 3]},  # JSON válido pero no es un objeto
            {"data": "{malformado", "content_type": "application/json"},  # JSON roto
        ],
    )
    def test_rejects_json_that_is_not_a_valid_object(self, client, service_calls, kwargs):
        response = client.post(f"{API}/passwords/generate", **kwargs)

        assert response.status_code == 400
        assert response.get_json()["error"]["details"] == {
            "body": "Debe ser un objeto JSON válido."
        }
        assert service_calls["generate"] == []


class TestStrengthRoute:
    def test_passes_the_password_to_the_service(self, client, service_calls):
        # Act
        client.post(f"{API}/passwords/strength", json={"password": "MiClave#2026"})

        # Assert
        assert service_calls["evaluate"] == ["MiClave#2026"]

    def test_returns_the_service_result_as_json(self, client, service_calls):
        response = client.post(f"{API}/passwords/strength", json={"password": "abc"})

        assert response.status_code == 200
        assert response.get_json() == {
            "score": 1,
            "label": "débil",
            "entropy_bits": 30.0,
            "feedback": ["consejo"],
        }

    def test_service_is_not_called_when_password_is_missing(self, client, service_calls):
        response = client.post(f"{API}/passwords/strength", json={})

        assert response.status_code == 400
        assert service_calls["evaluate"] == []
