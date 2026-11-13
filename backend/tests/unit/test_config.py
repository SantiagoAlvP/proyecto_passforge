"""Pruebas UNITARIAS de app/config.py

Prueban cada función y clase de configuración por separado. Las variables de
entorno se controlan con ``monkeypatch`` para que cada prueba sea
independiente de la terminal donde se ejecuta.
"""

import pytest

import app.config as config_module
from app.config import (
    DEFAULT_DEV_ORIGINS,
    DevelopmentConfig,
    ProductionConfig,
    _parse_bool,
    _parse_list,
    get_config,
)

# Se usa a través del módulo: si se importara directamente, pytest intentaría
# recolectar la clase "TestingConfig" como si fuera una clase de pruebas.
TESTING_CONFIG = config_module.TestingConfig

pytestmark = pytest.mark.unit

DEV_ORIGINS = DEFAULT_DEV_ORIGINS.split(",")


class TestParseList:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("a,b", ["a", "b"]),
            (" a , b ,, ", ["a", "b"]),  # quita espacios y elementos vacíos
            ("", []),
        ],
    )
    def test_parse_list(self, raw, expected):
        assert _parse_list(raw) == expected


class TestParseBool:
    @pytest.mark.parametrize("raw", ["1", "true", "TRUE", " yes ", "on"])
    def test_truthy_values(self, raw):
        assert _parse_bool(raw) is True

    @pytest.mark.parametrize("raw", ["0", "false", "no", "", "cualquier-cosa"])
    def test_falsy_values(self, raw):
        assert _parse_bool(raw) is False

    def test_missing_value_returns_the_default(self):
        assert _parse_bool(None) is False
        assert _parse_bool(None, default=True) is True


class TestGetConfig:
    def test_development_config(self):
        # Act
        config = get_config("development")

        # Assert
        assert isinstance(config, DevelopmentConfig)
        assert config.DEBUG is True
        assert config.CORS_ORIGINS == DEV_ORIGINS

    def test_testing_config_disables_rate_limit(self):
        config = get_config("testing")

        assert isinstance(config, TESTING_CONFIG)
        assert config.TESTING is True
        assert config.RATELIMIT_ENABLED is False

    def test_environment_name_ignores_case_and_spaces(self):
        assert isinstance(get_config("  Testing "), TESTING_CONFIG)

    def test_uses_app_env_variable_when_no_name_is_given(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("APP_ENV", "development")

        # Act
        config = get_config()

        # Assert
        assert isinstance(config, DevelopmentConfig)

    def test_defaults_to_production_when_nothing_is_configured(self, monkeypatch):
        # Arrange: sin APP_ENV; producción exige CORS_ORIGINS
        monkeypatch.setenv("CORS_ORIGINS", "https://passforge.example")

        # Act
        config = get_config()

        # Assert: la opción por defecto es la más segura
        assert isinstance(config, ProductionConfig)
        assert config.DEBUG is False
        assert config.HSTS_ENABLED is True

    def test_unknown_environment_raises_error(self):
        with pytest.raises(ValueError, match="staging"):
            get_config("staging")

    def test_reads_values_from_environment_variables(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("CORS_ORIGINS", "http://a.example, http://b.example")
        monkeypatch.setenv("RATELIMIT_DEFAULT", "5/minute")
        monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://redis:6379")
        monkeypatch.setenv("TRUST_PROXY", "true")
        monkeypatch.setenv("LOG_LEVEL", "warning")

        # Act
        config = get_config("testing")

        # Assert
        assert config.CORS_ORIGINS == ["http://a.example", "http://b.example"]
        assert config.RATELIMIT_DEFAULT == "5/minute"
        assert config.RATELIMIT_STORAGE_URI == "redis://redis:6379"
        assert config.TRUST_PROXY is True
        assert config.LOG_LEVEL == "WARNING"

    def test_uses_safe_defaults_when_variables_are_missing(self):
        config = get_config("testing")

        assert config.RATELIMIT_DEFAULT == "60/minute"
        assert config.RATELIMIT_STORAGE_URI == "memory://"
        assert config.TRUST_PROXY is False
        assert config.MAX_CONTENT_LENGTH == 2 * 1024


class TestProductionConfigValidation:
    def test_requires_cors_origins(self):
        # Arrange: CORS_ORIGINS no está definida (la fixture limpia el entorno)
        config = ProductionConfig()

        # Act / Assert
        with pytest.raises(RuntimeError, match="obligatorio"):
            config.validate()

    def test_rejects_wildcard_origin(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "*")

        with pytest.raises(RuntimeError, match=r"'\*'"):
            ProductionConfig().validate()

    def test_accepts_explicit_origins(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://passforge.example")

        ProductionConfig().validate()  # no lanza ninguna excepción

    def test_other_environments_do_not_require_cors_origins(self):
        DevelopmentConfig().validate()
        TESTING_CONFIG().validate()
