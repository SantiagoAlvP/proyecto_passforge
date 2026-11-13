"""Pruebas UNITARIAS de app/validators.py

Verifican cada función de validación por separado: los datos válidos se
convierten en el objeto esperado y los inválidos se rechazan con un mensaje
claro por cada campo.
"""

import pytest

from app.errors import ValidationError
from app.services.password_service import PasswordOptions
from app.validators import parse_generate_payload, parse_strength_payload

pytestmark = pytest.mark.unit


class TestParseGeneratePayload:
    def test_empty_payload_uses_default_options(self):
        # Arrange
        payload = {}

        # Act
        options = parse_generate_payload(payload)

        # Assert
        assert options == PasswordOptions()

    def test_valid_payload_is_converted_to_options(self):
        # Arrange
        payload = {"length": 24, "include_symbols": False, "exclude_ambiguous": True}

        # Act
        options = parse_generate_payload(payload)

        # Assert
        assert options == PasswordOptions(
            length=24, include_symbols=False, exclude_ambiguous=True
        )

    @pytest.mark.parametrize("length", [7, 129, 0, -5])
    def test_rejects_length_out_of_range(self, length):
        # Act
        with pytest.raises(ValidationError) as error:
            parse_generate_payload({"length": length})

        # Assert
        assert error.value.details == {"length": "Debe estar entre 8 y 128."}

    @pytest.mark.parametrize("length", ["16", 16.5, None, True])
    def test_rejects_length_that_is_not_an_integer(self, length):
        # True se prueba a propósito: en Python bool es subclase de int.
        with pytest.raises(ValidationError) as error:
            parse_generate_payload({"length": length})

        assert error.value.details == {"length": "Debe ser un número entero."}

    @pytest.mark.parametrize("value", ["true", 1, None])
    def test_rejects_flags_that_are_not_booleans(self, value):
        with pytest.raises(ValidationError) as error:
            parse_generate_payload({"include_digits": value})

        assert error.value.details == {"include_digits": "Debe ser true o false."}

    def test_rejects_unknown_fields(self):
        with pytest.raises(ValidationError) as error:
            parse_generate_payload({"color": "rojo"})

        assert error.value.details == {"color": "Campo no permitido."}

    def test_requires_at_least_one_character_set(self):
        # Arrange
        payload = {
            "include_lowercase": False,
            "include_uppercase": False,
            "include_digits": False,
            "include_symbols": False,
        }

        # Act
        with pytest.raises(ValidationError) as error:
            parse_generate_payload(payload)

        # Assert
        assert error.value.details == {
            "character_sets": "Selecciona al menos un tipo de carácter."
        }

    def test_reports_all_errors_at_once(self):
        with pytest.raises(ValidationError) as error:
            parse_generate_payload({"length": 2, "include_symbols": "no", "extra": 1})

        assert set(error.value.details) == {"length", "include_symbols", "extra"}


class TestParseStrengthPayload:
    def test_returns_the_password(self):
        # Act
        password = parse_strength_payload({"password": "MiClave#2026"})

        # Assert
        assert password == "MiClave#2026"

    @pytest.mark.parametrize("password", ["x", "x" * 128])
    def test_accepts_length_limits(self, password):
        assert parse_strength_payload({"password": password}) == password

    @pytest.mark.parametrize("payload", [{}, {"password": None}, {"password": 123}])
    def test_rejects_missing_or_non_text_password(self, payload):
        with pytest.raises(ValidationError) as error:
            parse_strength_payload(payload)

        assert error.value.details == {"password": "Es obligatorio y debe ser texto."}

    @pytest.mark.parametrize("password", ["", "x" * 129])
    def test_rejects_password_with_invalid_length(self, password):
        with pytest.raises(ValidationError) as error:
            parse_strength_payload({"password": password})

        assert error.value.details == {"password": "Debe tener entre 1 y 128 caracteres."}

    def test_rejects_unknown_fields(self):
        with pytest.raises(ValidationError) as error:
            parse_strength_payload({"password": "abc", "user": "santiago"})

        assert error.value.details == {"user": "Campo no permitido."}
