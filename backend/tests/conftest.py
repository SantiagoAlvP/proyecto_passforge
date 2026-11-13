"""Fixtures compartidas por todas las pruebas (unitarias, modulares y de integración).

Una *fixture* es una función que prepara algo que las pruebas necesitan (la
parte "Arrange" reutilizable). pytest la inyecta automáticamente en cualquier
prueba que tenga un parámetro con el mismo nombre.
"""

import pytest

from app import create_app

# Variables de entorno que cambian la configuración de la app.
APP_ENV_VARS = (
    "APP_ENV",
    "CORS_ORIGINS",
    "RATELIMIT_DEFAULT",
    "RATELIMIT_STORAGE_URI",
    "TRUST_PROXY",
    "LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Aísla cada prueba de las variables de entorno de tu terminal.

    ``autouse=True`` la aplica a TODAS las pruebas sin tener que pedirla.
    ``monkeypatch`` deshace los cambios automáticamente al terminar.
    """
    for name in APP_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def app():
    """Una instancia NUEVA de la app, en modo testing, para cada prueba."""
    return create_app("testing")


@pytest.fixture
def client(app):
    """Cliente HTTP de pruebas de Flask.

    Envía peticiones a la app en memoria: no levanta un servidor ni usa la
    red, por eso las pruebas son rápidas y aisladas.
    """
    return app.test_client()


@pytest.fixture
def make_app(monkeypatch):
    """Fábrica para crear apps con un entorno o configuración específicos.

    Ejemplos::

        make_app(RATELIMIT_ENABLED=True)
        make_app("production", env={"CORS_ORIGINS": "https://passforge.example"})
    """

    def _make_app(env_name="testing", env=None, **overrides):
        for name, value in (env or {}).items():
            monkeypatch.setenv(name, value)
        return create_app(env_name, overrides=overrides or None)

    return _make_app
