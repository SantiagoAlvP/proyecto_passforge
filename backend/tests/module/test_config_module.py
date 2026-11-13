"""Pruebas MODULARES del módulo de configuración: app/config.py

Se prueba el módulo completo tal como lo usa Flask: se lee el entorno, se
crea la configuración y se carga en una app Flask VACÍA (no en PassForge),
para comprobar que el módulo funciona por sí solo.
"""

import pytest
from flask import Flask

from app.config import get_config

pytestmark = pytest.mark.module


def load_into_flask(env_name=None):
    """Carga la configuración en una app Flask vacía y devuelve su config."""
    flask_app = Flask(__name__)
    flask_app.config.from_object(get_config(env_name))
    return flask_app.config


class TestConfigurationLoadedIntoFlask:
    def test_only_uppercase_settings_are_loaded(self):
        # Act
        config = load_into_flask("development")

        # Assert: Flask solo carga atributos en MAYÚSCULAS
        assert config["DEBUG"] is True
        assert "CORS_ORIGINS" in config
        assert "default_cors_origins" not in config

    def test_development_environment_built_from_variables(self, monkeypatch):
        # Arrange: así se configuraría desde un .env o desde Docker
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
        monkeypatch.setenv("RATELIMIT_DEFAULT", "10/minute")
        monkeypatch.setenv("TRUST_PROXY", "yes")

        # Act
        config = load_into_flask()

        # Assert
        assert config["DEBUG"] is True
        assert config["CORS_ORIGINS"] == ["http://localhost:3000"]
        assert config["RATELIMIT_DEFAULT"] == "10/minute"
        assert config["TRUST_PROXY"] is True

    def test_production_is_secure_by_default(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("CORS_ORIGINS", "https://passforge.example")

        # Act: sin APP_ENV
        config = load_into_flask()

        # Assert
        assert config["DEBUG"] is False
        assert config["TESTING"] is False
        assert config["HSTS_ENABLED"] is True
        assert config["RATELIMIT_ENABLED"] is True
        assert config["MAX_CONTENT_LENGTH"] == 2 * 1024

    def test_each_load_reads_the_current_environment(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("CORS_ORIGINS", "http://primero.example")
        first = load_into_flask("testing")

        # Act: cambia el entorno y se vuelve a cargar
        monkeypatch.setenv("CORS_ORIGINS", "http://segundo.example")
        second = load_into_flask("testing")

        # Assert: los valores no quedaron "congelados" al importar el módulo
        assert first["CORS_ORIGINS"] == ["http://primero.example"]
        assert second["CORS_ORIGINS"] == ["http://segundo.example"]

    @pytest.mark.parametrize("unsafe_origins", ["", "*", "https://ok.example,*"])
    def test_production_refuses_unsafe_cors_settings(self, monkeypatch, unsafe_origins):
        monkeypatch.setenv("CORS_ORIGINS", unsafe_origins)

        with pytest.raises(RuntimeError):
            load_into_flask("production")
