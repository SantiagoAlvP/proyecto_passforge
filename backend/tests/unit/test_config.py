"""Pruebas de la configuración por entorno y de la application factory."""

from __future__ import annotations

import pytest

from app import create_app
from app import config as cfg
from app.config import get_config


@pytest.mark.parametrize(
    ("name", "expected_class"),
    [
        ("development", cfg.DevelopmentConfig),
        ("testing", cfg.TestingConfig),
        (" Testing ", cfg.TestingConfig),  # ignora espacios y mayúsculas
    ],
)
def test_get_config_by_name(name, expected_class):
    assert isinstance(get_config(name), expected_class)


def test_get_config_uses_app_env_variable(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")

    assert isinstance(get_config(), cfg.DevelopmentConfig)


def test_get_config_unknown_env_raises():
    with pytest.raises(ValueError, match="Entorno desconocido"):
        get_config("staging")


def test_config_reads_environment_variables(monkeypatch):
    # Arrange
    monkeypatch.setenv("CORS_ORIGINS", " http://a.com , ,http://b.com")
    monkeypatch.setenv("TRUST_PROXY", "yes")
    monkeypatch.setenv("LOG_LEVEL", "warning")

    # Act
    config = get_config("testing")

    # Assert
    assert config.CORS_ORIGINS == ["http://a.com", "http://b.com"]
    assert config.TRUST_PROXY is True
    assert config.LOG_LEVEL == "WARNING"


def test_production_requires_cors_origins(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    with pytest.raises(RuntimeError, match="obligatorio"):
        get_config("production")


def test_production_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="no puede ser"):
        get_config("production")


def test_production_app_enables_hsts(monkeypatch):
    # Arrange
    monkeypatch.setenv("CORS_ORIGINS", "https://passforge.example")

    # Act
    app = create_app("production")
    response = app.test_client().get("/api/v1/health")

    # Assert
    assert isinstance(get_config("production"), cfg.ProductionConfig)
    assert "max-age" in response.headers["Strict-Transport-Security"]


def test_create_app_applies_overrides_and_proxy_fix():
    # Act
    app = create_app("testing", overrides={"TRUST_PROXY": True, "FOO": "bar"})

    # Assert
    assert app.config["FOO"] == "bar"
    assert type(app.wsgi_app).__name__ == "ProxyFix"
