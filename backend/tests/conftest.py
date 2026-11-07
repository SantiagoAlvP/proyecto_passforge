"""Fixtures compartidas por todas las pruebas."""

from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app


@pytest.fixture
def app() -> Flask:
    """Una instancia nueva y aislada de la app para cada prueba.

    Se usa la configuración ``testing`` (sin rate limit) gracias a la
    application factory ``create_app``.
    """
    return create_app("testing")


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Cliente HTTP de prueba: hace peticiones sin levantar un servidor real."""
    return app.test_client()
