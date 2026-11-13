"""Pruebas de INTEGRACIÓN de la API.

Usan la app COMPLETA creada con create_app(), SIN dobles de prueba: cada
petición atraviesa todas las capas reales juntas:

    CORS -> rate limiter -> ruta -> validador -> servicio
         -> manejo de errores -> cabeceras de seguridad -> respuesta JSON

Las piezas ya se probaron por separado (unitarias y modulares); aquí se
verifica que funcionan bien cuando se combinan.
"""

import logging
import string

import pytest

pytestmark = pytest.mark.integration

API = "/api/v1"
FRONTEND_ORIGIN = "http://127.0.0.1:5500"


class TestCompleteFlows:
    def test_frontend_flow_policy_then_generate_then_check(self, client):
        """El mismo recorrido que hace el frontend al usar la app."""
        # Arrange: el frontend pide la política para armar el formulario
        policy = client.get(f"{API}/passwords/options").get_json()
        max_length = policy["length"]["max"]

        # Act: genera con la longitud máxima y luego comprueba esa contraseña
        generated = client.post(f"{API}/passwords/generate", json={"length": max_length})
        password = generated.get_json()["password"]
        checked = client.post(f"{API}/passwords/strength", json={"password": password})

        # Assert
        assert generated.status_code == 200
        assert len(password) == max_length
        assert generated.get_json()["strength"]["label"] == "muy fuerte"
        assert checked.status_code == 200
        assert checked.get_json()["label"] in policy["strength_labels"]
        assert checked.get_json()["entropy_bits"] > 128

    @pytest.mark.parametrize("which", ["min", "default", "max"])
    def test_every_length_published_by_the_policy_works(self, client, which):
        # Arrange
        length = client.get(f"{API}/passwords/options").get_json()["length"][which]

        # Act
        response = client.post(f"{API}/passwords/generate", json={"length": length})

        # Assert
        assert response.status_code == 200
        assert response.get_json()["length"] == length

    def test_combined_options_are_respected_end_to_end(self, client):
        # Arrange
        payload = {
            "length": 40,
            "include_uppercase": False,
            "include_symbols": False,
            "exclude_ambiguous": True,
        }

        # Act
        password = client.post(f"{API}/passwords/generate", json=payload).get_json()["password"]

        # Assert
        allowed = set(string.ascii_lowercase + string.digits) - set("Il1O0o")
        assert len(password) == 40
        assert set(password) <= allowed

    def test_common_password_is_reported_as_very_weak(self, client):
        response = client.post(f"{API}/passwords/strength", json={"password": "qwerty"})

        assert response.get_json()["label"] == "muy débil"


class TestErrorsThroughTheWholeStack:
    @pytest.mark.parametrize(
        ("request_kwargs", "status", "code"),
        [
            ({"json": {"length": 4}}, 400, "validation_error"),
            ({"json": ["no", "es", "objeto"]}, 400, "validation_error"),
            ({"data": "{malformado", "content_type": "application/json"}, 400, "validation_error"),
            ({"data": "length=16", "content_type": "text/plain"}, 415, "unsupported_media_type"),
            ({"data": "x" * 5000, "content_type": "application/json"}, 413, "request_entity_too_large"),
        ],
        ids=["invalid-length", "not-an-object", "broken-json", "not-json", "too-large"],
    )
    def test_errors_have_uniform_format_and_security_headers(
        self, client, request_kwargs, status, code
    ):
        # Act
        response = client.post(f"{API}/passwords/generate", **request_kwargs)

        # Assert
        assert response.status_code == status
        assert response.get_json()["error"]["code"] == code
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Cache-Control"] == "no-store"

    def test_wrong_method_and_unknown_route(self, client):
        assert client.get(f"{API}/passwords/strength").status_code == 405
        assert client.get(f"{API}/passwords/no-existe").status_code == 404


class TestCorsIntegration:
    def test_preflight_from_the_frontend_is_authorized(self, client):
        # Act: el navegador envía esta petición OPTIONS antes de un POST con JSON
        response = client.options(
            f"{API}/passwords/generate",
            headers={
                "Origin": FRONTEND_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Assert
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == FRONTEND_ORIGIN
        assert "POST" in response.headers["Access-Control-Allow-Methods"]
        assert "content-type" in response.headers["Access-Control-Allow-Headers"].lower()

    def test_preflight_from_another_site_is_not_authorized(self, client):
        response = client.options(
            f"{API}/passwords/generate",
            headers={
                "Origin": "https://sitio-malicioso.com",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert "Access-Control-Allow-Origin" not in response.headers

    def test_error_responses_also_carry_cors_headers(self, client):
        """Sin esto, el frontend no podría leer el mensaje de error."""
        response = client.post(
            f"{API}/passwords/generate",
            json={"length": 4},
            headers={"Origin": FRONTEND_ORIGIN},
        )

        assert response.status_code == 400
        assert response.headers["Access-Control-Allow-Origin"] == FRONTEND_ORIGIN


class TestRateLimitIntegration:
    STRENGTH = f"{API}/passwords/strength"
    PAYLOAD = {"password": "abc12345"}

    def test_each_endpoint_has_its_own_limit(self, make_app):
        # Arrange
        client = make_app(RATELIMIT_ENABLED=True).test_client()

        # Act: se agota el límite (30/min) de /strength
        for _ in range(30):
            client.post(self.STRENGTH, json=self.PAYLOAD)
        blocked = client.post(self.STRENGTH, json=self.PAYLOAD)

        # Assert
        assert blocked.status_code == 429
        assert blocked.get_json()["error"]["code"] == "too_many_requests"
        assert "Retry-After" in blocked.headers
        assert blocked.headers["X-Content-Type-Options"] == "nosniff"
        # los demás endpoints siguen disponibles y /health está exento
        assert client.post(f"{API}/passwords/generate", json={}).status_code == 200
        assert client.get(f"{API}/health").status_code == 200

    def test_forged_forwarded_header_cannot_bypass_the_limit(self, make_app):
        """Sin TRUST_PROXY, un atacante no puede 'cambiar de IP' con X-Forwarded-For."""
        # Arrange
        client = make_app(RATELIMIT_ENABLED=True).test_client()

        # Act
        for i in range(30):
            client.post(self.STRENGTH, json=self.PAYLOAD, headers={"X-Forwarded-For": f"203.0.113.{i}"})
        response = client.post(
            self.STRENGTH, json=self.PAYLOAD, headers={"X-Forwarded-For": "198.51.100.7"}
        )

        # Assert
        assert response.status_code == 429

    def test_behind_a_trusted_proxy_each_client_ip_has_its_own_limit(self, make_app):
        # Arrange
        client = make_app(RATELIMIT_ENABLED=True, TRUST_PROXY=True).test_client()
        client_a = {"X-Forwarded-For": "203.0.113.10"}
        client_b = {"X-Forwarded-For": "203.0.113.20"}

        # Act
        for _ in range(30):
            client.post(self.STRENGTH, json=self.PAYLOAD, headers=client_a)

        # Assert
        assert client.post(self.STRENGTH, json=self.PAYLOAD, headers=client_a).status_code == 429
        assert client.post(self.STRENGTH, json=self.PAYLOAD, headers=client_b).status_code == 200


class TestSecurityIntegration:
    def test_passwords_never_appear_in_the_logs(self, client, caplog):
        # Act
        with caplog.at_level(logging.DEBUG):
            generated = client.post(f"{API}/passwords/generate", json={}).get_json()["password"]
            client.post(f"{API}/passwords/strength", json={"password": "MiSecreto#2026"})

        # Assert
        assert generated not in caplog.text
        assert "MiSecreto#2026" not in caplog.text

    def test_production_app_end_to_end(self, make_app):
        # Arrange
        app = make_app("production", env={"CORS_ORIGINS": "https://passforge.example"})
        client = app.test_client()

        # Act
        allowed = client.get(f"{API}/health", headers={"Origin": "https://passforge.example"})
        dev_origin = client.get(f"{API}/health", headers={"Origin": FRONTEND_ORIGIN})

        # Assert
        assert app.debug is False
        assert allowed.headers["Strict-Transport-Security"].startswith("max-age=")
        assert allowed.headers["Access-Control-Allow-Origin"] == "https://passforge.example"
        assert "Access-Control-Allow-Origin" not in dev_origin.headers

    def test_production_app_refuses_to_start_without_cors_origins(self, make_app):
        with pytest.raises(RuntimeError):
            make_app("production")
