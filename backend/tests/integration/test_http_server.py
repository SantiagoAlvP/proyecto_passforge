"""Pruebas de INTEGRACIÓN con un servidor HTTP REAL.

Las demás pruebas usan el cliente de pruebas de Flask, que llama a la app en
memoria. Aquí se levanta un servidor de verdad en un puerto libre y se le
hacen peticiones por la red local con ``urllib`` (como haría curl o un
navegador), para verificar la app tal como se ejecuta: sockets, cabeceras y
JSON reales.
"""

import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest
from werkzeug.serving import make_server

from app import create_app

pytestmark = pytest.mark.integration

# Abridor sin proxy: las peticiones a 127.0.0.1 nunca deben salir de la máquina.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@pytest.fixture
def base_url():
    """Levanta la app en un servidor real y lo apaga al terminar la prueba."""
    server = make_server("127.0.0.1", 0, create_app("testing"), threaded=True)  # 0 = puerto libre
    # poll_interval corto para que el servidor se apague rápido al terminar.
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/api/v1"
    server.shutdown()
    thread.join(timeout=5)


def http(method, url, payload=None, headers=None):
    """Hace una petición HTTP real. Devuelve (status, cabeceras, cuerpo JSON)."""
    headers = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with _OPENER.open(request, timeout=5) as response:
            return response.status, response.headers, json.loads(response.read())
    except urllib.error.HTTPError as error:  # urllib lanza excepción en 4xx/5xx
        return error.code, error.headers, json.loads(error.read())


class TestRealHttpServer:
    def test_health_check(self, base_url):
        # Act
        status, headers, body = http("GET", f"{base_url}/health")

        # Assert
        assert status == 200
        assert body == {"status": "ok"}
        assert headers["Content-Type"] == "application/json"

    def test_generate_and_check_over_the_network(self, base_url):
        # Act
        status, _, generated = http("POST", f"{base_url}/passwords/generate", {"length": 24})
        _, _, checked = http("POST", f"{base_url}/passwords/strength", {"password": generated["password"]})

        # Assert
        assert status == 200
        assert len(generated["password"]) == 24
        assert checked["entropy_bits"] > 0

    def test_validation_error_over_the_network(self, base_url):
        status, _, body = http("POST", f"{base_url}/passwords/generate", {"length": 2})

        assert status == 400
        assert body["error"]["code"] == "validation_error"

    def test_security_and_cors_headers_over_the_network(self, base_url):
        _, headers, _ = http("GET", f"{base_url}/health", headers={"Origin": "http://127.0.0.1:5500"})

        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Cache-Control"] == "no-store"
        assert headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5500"

    def test_server_handles_concurrent_requests(self, base_url):
        # Arrange
        def generate(_):
            return http("POST", f"{base_url}/passwords/generate", {})

        # Act: 20 peticiones en paralelo
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(generate, range(20)))

        # Assert: todas responden bien y cada contraseña es distinta
        assert {status for status, _, _ in results} == {200}
        assert len({body["password"] for _, _, body in results}) == 20
