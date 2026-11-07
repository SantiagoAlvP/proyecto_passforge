"""Validación de los datos que llegan en las peticiones HTTP.

Principio de seguridad: *nunca confiar en la entrada del cliente*. Se valida
el tipo, el rango y que no lleguen campos desconocidos (lista blanca).
"""

from __future__ import annotations

from typing import Any

from app.errors import ValidationError
from app.services.password_service import (
    DEFAULT_LENGTH,
    MAX_LENGTH,
    MAX_PASSWORD_INPUT_LENGTH,
    MIN_LENGTH,
    PasswordOptions,
)

_CHARSET_FIELDS = (
    "include_lowercase",
    "include_uppercase",
    "include_digits",
    "include_symbols",
)
_BOOLEAN_DEFAULTS = {
    "include_lowercase": True,
    "include_uppercase": True,
    "include_digits": True,
    "include_symbols": True,
    "exclude_ambiguous": False,
}
_GENERATE_FIELDS = frozenset({"length", *_BOOLEAN_DEFAULTS})
_STRENGTH_FIELDS = frozenset({"password"})


def _is_integer(value: Any) -> bool:
    # En Python ``True`` es un ``int``; aquí no lo aceptamos como número.
    return isinstance(value, int) and not isinstance(value, bool)


def _check_unknown_fields(data: dict[str, Any], allowed: frozenset[str]) -> dict[str, str]:
    return {
        name: "Campo no permitido."
        for name in sorted(data)
        if name not in allowed
    }


def parse_generate_payload(data: dict[str, Any]) -> PasswordOptions:
    """Valida el cuerpo de ``POST /passwords/generate``.

    Todos los campos son opcionales; los ausentes toman su valor por defecto.
    """
    errors = _check_unknown_fields(data, _GENERATE_FIELDS)

    length = data.get("length", DEFAULT_LENGTH)
    if not _is_integer(length):
        errors["length"] = "Debe ser un número entero."
    elif not MIN_LENGTH <= length <= MAX_LENGTH:
        errors["length"] = f"Debe estar entre {MIN_LENGTH} y {MAX_LENGTH}."

    flags: dict[str, bool] = {}
    for name, default in _BOOLEAN_DEFAULTS.items():
        value = data.get(name, default)
        if isinstance(value, bool):
            flags[name] = value
        else:
            errors[name] = "Debe ser true o false."

    if len(flags) == len(_BOOLEAN_DEFAULTS) and not any(
        flags[name] for name in _CHARSET_FIELDS
    ):
        errors["character_sets"] = "Selecciona al menos un tipo de carácter."

    if errors:
        raise ValidationError(errors)
    return PasswordOptions(length=length, **flags)


def parse_strength_payload(data: dict[str, Any]) -> str:
    """Valida el cuerpo de ``POST /passwords/strength`` y devuelve la contraseña."""
    errors = _check_unknown_fields(data, _STRENGTH_FIELDS)

    password = data.get("password")
    if not isinstance(password, str):
        errors["password"] = "Es obligatorio y debe ser texto."
    elif not 1 <= len(password) <= MAX_PASSWORD_INPUT_LENGTH:
        errors["password"] = (
            f"Debe tener entre 1 y {MAX_PASSWORD_INPUT_LENGTH} caracteres."
        )

    if errors:
        raise ValidationError(errors)
    return password
