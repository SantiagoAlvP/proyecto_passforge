"""Configuración de la aplicación por entorno.

Los valores que cambian entre entornos (o que podrían ser sensibles) se leen
de variables de entorno, nunca se escriben en el código (principio 12-factor).
Los valores se leen al *crear* la configuración y no al importar el módulo,
para que cada instancia de la app (por ejemplo, en pruebas) vea el entorno
actual.
"""

from __future__ import annotations

import os

DEFAULT_DEV_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"


def _parse_list(raw: str) -> list[str]:
    """Convierte ``"a, b,c"`` en ``["a", "b", "c"]`` ignorando vacíos."""
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    """Valores comunes a todos los entornos. Seguro por defecto."""

    DEBUG = False
    TESTING = False

    # Tamaño máximo del cuerpo de una petición: evita abusos con payloads
    # gigantes. Las peticiones de esta API ocupan unos pocos bytes.
    MAX_CONTENT_LENGTH = 2 * 1024  # 2 KB

    RATELIMIT_ENABLED = True
    RATELIMIT_HEADERS_ENABLED = True
    HSTS_ENABLED = False
    LOG_LEVEL = "INFO"

    # En minúsculas para que Flask no lo cargue como clave de configuración.
    default_cors_origins = ""

    def __init__(self) -> None:
        self.CORS_ORIGINS = _parse_list(
            os.getenv("CORS_ORIGINS", self.default_cors_origins)
        )
        self.RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "60/minute")
        self.RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
        # Activar solo si la app corre detrás de un proxy de confianza (nginx),
        # para que el rate limit use la IP real del cliente.
        self.TRUST_PROXY = _parse_bool(os.getenv("TRUST_PROXY"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", self.LOG_LEVEL).upper()

    def validate(self) -> None:
        """Comprueba la configuración. Las subclases pueden ser más estrictas."""


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    default_cors_origins = DEFAULT_DEV_ORIGINS


class TestingConfig(BaseConfig):
    TESTING = True
    # Las pruebas hacen muchas peticiones seguidas: no deben ser bloqueadas.
    RATELIMIT_ENABLED = False
    default_cors_origins = DEFAULT_DEV_ORIGINS


class ProductionConfig(BaseConfig):
    HSTS_ENABLED = True

    def validate(self) -> None:
        # "Fail fast": mejor no arrancar que arrancar con una config insegura.
        if not self.CORS_ORIGINS:
            raise RuntimeError("CORS_ORIGINS es obligatorio en producción.")
        if "*" in self.CORS_ORIGINS:
            raise RuntimeError("CORS_ORIGINS no puede ser '*' en producción.")


_CONFIGS: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None) -> BaseConfig:
    """Devuelve la configuración del entorno indicado (o de ``APP_ENV``).

    Si no se indica nada se usa ``production``: la opción más segura.
    """
    name = (env_name or os.getenv("APP_ENV", "production")).strip().lower()
    try:
        config_class = _CONFIGS[name]
    except KeyError as exc:
        valid = ", ".join(_CONFIGS)
        raise ValueError(f"Entorno desconocido {name!r}. Usa uno de: {valid}.") from exc

    config = config_class()
    config.validate()
    return config
