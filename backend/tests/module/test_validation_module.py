"""Pruebas MODULARES del módulo de validación: app/validators.py

El módulo se prueba completo como "puerta de entrada" de la API, sin Flask
ni HTTP:
  - hace cumplir cada regla que publica la política del servicio, y
  - todo lo que deja pasar produce opciones con las que el generador funciona.
"""

from itertools import combinations

import pytest

from app.errors import ValidationError
from app.services.password_service import (
    PasswordOptions,
    build_character_sets,
    evaluate_strength,
    generate_password,
    get_password_policy,
)
from app.validators import parse_generate_payload, parse_strength_payload

pytestmark = pytest.mark.module

CHARSET_FIELDS = ("include_lowercase", "include_uppercase", "include_digits", "include_symbols")
ALL_CHARSET_COMBINATIONS = [
    combo for size in range(1, 5) for combo in combinations(CHARSET_FIELDS, size)
]


class TestValidationEnforcesThePublishedPolicy:
    def test_length_limits_from_the_policy(self):
        # Arrange
        limits = get_password_policy()["length"]

        # Act / Assert
        assert parse_generate_payload({"length": limits["min"]}).length == limits["min"]
        assert parse_generate_payload({"length": limits["max"]}).length == limits["max"]
        for invalid in (limits["min"] - 1, limits["max"] + 1):
            with pytest.raises(ValidationError):
                parse_generate_payload({"length": invalid})

    def test_a_payload_with_every_published_default_gives_default_options(self):
        # Arrange: se arma el payload solo con lo que publica la política
        policy = get_password_policy()
        payload = {
            "length": policy["length"]["default"],
            "exclude_ambiguous": policy["exclude_ambiguous"]["default"],
            **{name: info["default"] for name, info in policy["character_sets"].items()},
        }

        # Act
        options = parse_generate_payload(payload)

        # Assert
        assert options == PasswordOptions()

    def test_maximum_input_length_from_the_policy(self):
        maximum = get_password_policy()["max_password_input_length"]

        assert parse_strength_payload({"password": "x" * maximum})
        with pytest.raises(ValidationError):
            parse_strength_payload({"password": "x" * (maximum + 1)})


class TestValidatedDataWorksWithTheService:
    @pytest.mark.parametrize("exclude_ambiguous", [False, True])
    @pytest.mark.parametrize(
        "charsets", ALL_CHARSET_COMBINATIONS, ids=lambda c: "+".join(n[8:] for n in c)
    )
    def test_any_valid_payload_produces_a_usable_password(self, charsets, exclude_ambiguous):
        # Arrange
        payload = {
            "length": 10,
            "exclude_ambiguous": exclude_ambiguous,
            **{name: name in charsets for name in CHARSET_FIELDS},
        }

        # Act
        options = parse_generate_payload(payload)
        password = generate_password(options)

        # Assert
        allowed = set("".join(build_character_sets(options)))
        assert len(password) == 10
        assert set(password) <= allowed

    @pytest.mark.parametrize("text", ["a", "123456", "contraseña", "T7#qL!m9$zR2@vX8", "ñ" * 128])
    def test_any_accepted_password_can_be_evaluated(self, text):
        # Arrange
        labels = get_password_policy()["strength_labels"]

        # Act
        result = evaluate_strength(parse_strength_payload({"password": text}))

        # Assert
        assert result.label in labels
        assert result.entropy_bits >= 0
