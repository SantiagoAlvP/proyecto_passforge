"""Pruebas UNITARIAS de create_app() en app/__init__.py

Verifican que la *application factory* construye la app con la configuración
pedida, sin hacer peticiones HTTP.
"""

import logging

import pytest
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app

pytestmark = pytest.mark.unit


class TestCreateApp:
    def test_uses_the_requested_environment(self):
        # Act
        app = create_app("testing")

        # Assert
        assert app.testing is True
        assert app.debug is False

    def test_overrides_replace_the_configuration(self):
        app = create_app("testing", overrides={"MAX_CONTENT_LENGTH": 10})

        assert app.config["MAX_CONTENT_LENGTH"] == 10

    def test_registers_the_api_blueprint(self):
        app = create_app("testing")

        assert "api" in app.blueprints

    def test_each_call_returns_a_new_independent_app(self):
        assert create_app("testing") is not create_app("testing")

    def test_does_not_trust_proxy_headers_by_default(self):
        app = create_app("testing")

        assert not isinstance(app.wsgi_app, ProxyFix)

    def test_wraps_the_app_with_proxyfix_when_trusting_a_proxy(self):
        app = create_app("testing", overrides={"TRUST_PROXY": True})

        assert isinstance(app.wsgi_app, ProxyFix)

    def test_sets_the_logger_level_from_the_configuration(self):
        app = create_app("testing", overrides={"LOG_LEVEL": "WARNING"})

        assert app.logger.level == logging.WARNING

    def test_json_keeps_key_order_and_accented_characters(self):
        app = create_app("testing")

        assert app.json.sort_keys is False
        assert app.json.ensure_ascii is False
