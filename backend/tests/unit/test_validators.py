"""Pruebas unitarias de la validación de entrada (``validators``)."""

from __future__ import annotations

import pytest

from app.errors import ValidationError
from app.services.password_service import PasswordOptions
from app.validators import parse_generate_payload, parse_strength_payload


def test_parse_generate_payload_empty_uses_defaults():
    # Act
    options = parse_generate_payload({})

    # Assert
    assert options == PasswordOptions()


def test_parse_generate_payload_accepts_valid_values():
    # Arrange
    data = {"length": 20, "include_symbols": False, "exclude_ambiguous": True}

    # Act
    options = parse_generate_payload(data)

    # Assert
    assert options.length == 20
    assert options.include_symbols is False
    assert options.exclude_ambiguous is True


@pytest.mark.parametrize(
    ("data", "field", "message"),
    [
        ({"length": "16"}, "length", "entero"),
        ({"length": True}, "length", "entero"),  # bool no cuenta como número
        ({"length": 7}, "length", "entre"),
        ({"length": 129}, "length", "entre"),
        ({"include_digits": "yes"}, "include_digits", "true o false"),
        ({"hack": 1}, "hack", "no permitido"),
    ],
)
def test_parse_generate_payload_rejects_invalid_fields(data, field, message):
    # Act
    with pytest.raises(ValidationError) as exc_info:
        parse_generate_payload(data)

    # Assert
    assert message in exc_info.value.details[field]


def test_parse_generate_payload_requires_a_charset():
    # Arrange
    data = {
        "include_lowercase": False,
        "include_uppercase": False,
        "include_digits": False,
        "include_symbols": False,
    }

    # Act / Assert
    with pytest.raises(ValidationError) as exc_info:
        parse_generate_payload(data)
    assert "character_sets" in exc_info.value.details


def test_parse_strength_payload_returns_password():
    assert parse_strength_payload({"password": "hola123"}) == "hola123"


@pytest.mark.parametrize(
    "data",
    [{}, {"password": 123}, {"password": ""}, {"password": "a" * 129}],
)
def test_parse_strength_payload_rejects_invalid_password(data):
    with pytest.raises(ValidationError) as exc_info:
        parse_strength_payload(data)
    assert "password" in exc_info.value.details


def test_parse_strength_payload_rejects_unknown_fields():
    with pytest.raises(ValidationError) as exc_info:
        parse_strength_payload({"password": "x", "extra": 1})
    assert exc_info.value.details == {"extra": "Campo no permitido."}
