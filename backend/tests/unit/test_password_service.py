"""Pruebas unitarias de la lógica de negocio (``password_service``).

Este módulo no depende de Flask, así que se prueba de forma totalmente
aislada: se llaman las funciones directamente y se verifica su resultado.
Cada prueba sigue la estrategia AAA (Arrange, Act, Assert).
"""

from __future__ import annotations

import pytest

from app.services import password_service as svc
from app.services.password_service import PasswordOptions


# --------------------------------------------------------------------------- #
# PasswordOptions
# --------------------------------------------------------------------------- #
def test_password_options_defaults_are_valid():
    # Arrange / Act
    options = PasswordOptions()

    # Assert
    assert options.length == svc.DEFAULT_LENGTH
    assert options.include_lowercase and options.include_symbols
    assert options.exclude_ambiguous is False


@pytest.mark.parametrize("length", [svc.MIN_LENGTH - 1, svc.MAX_LENGTH + 1])
def test_password_options_rejects_length_out_of_range(length):
    # Act / Assert
    with pytest.raises(ValueError, match="longitud"):
        PasswordOptions(length=length)


def test_password_options_requires_at_least_one_charset():
    # Act / Assert
    with pytest.raises(ValueError, match="al menos un tipo"):
        PasswordOptions(
            include_lowercase=False,
            include_uppercase=False,
            include_digits=False,
            include_symbols=False,
        )


# --------------------------------------------------------------------------- #
# Generación
# --------------------------------------------------------------------------- #
def test_build_character_sets_returns_only_selected_sets():
    # Arrange
    options = PasswordOptions(include_uppercase=False, include_symbols=False)

    # Act
    charsets = svc.build_character_sets(options)

    # Assert
    assert charsets == [svc.LOWERCASE, svc.DIGITS]


def test_build_character_sets_removes_ambiguous_characters():
    # Arrange
    options = PasswordOptions(exclude_ambiguous=True)

    # Act
    pool = "".join(svc.build_character_sets(options))

    # Assert
    assert not set(pool) & svc.AMBIGUOUS_CHARACTERS


@pytest.mark.parametrize("length", [svc.MIN_LENGTH, 16, svc.MAX_LENGTH])
def test_generate_password_has_requested_length(length):
    # Arrange
    options = PasswordOptions(length=length)

    # Act
    password = svc.generate_password(options)

    # Assert
    assert len(password) == length


def test_generate_password_contains_one_char_of_each_selected_set():
    # Arrange: longitud mínima para que la garantía sea exigente.
    options = PasswordOptions(length=svc.MIN_LENGTH)

    # Act: se repite varias veces porque el resultado es aleatorio.
    passwords = [svc.generate_password(options) for _ in range(50)]

    # Assert
    for password in passwords:
        assert any(ch in svc.LOWERCASE for ch in password)
        assert any(ch in svc.UPPERCASE for ch in password)
        assert any(ch in svc.DIGITS for ch in password)
        assert any(ch in svc.SYMBOLS for ch in password)


def test_generate_password_uses_only_allowed_characters():
    # Arrange
    options = PasswordOptions(
        length=64, include_uppercase=False, include_symbols=False,
        exclude_ambiguous=True,
    )
    allowed = set("".join(svc.build_character_sets(options)))

    # Act
    password = svc.generate_password(options)

    # Assert
    assert set(password) <= allowed


def test_generate_password_is_random():
    # Arrange
    options = PasswordOptions(length=32)

    # Act
    passwords = {svc.generate_password(options) for _ in range(20)}

    # Assert: 20 contraseñas de 32 caracteres no deberían repetirse nunca.
    assert len(passwords) == 20


# --------------------------------------------------------------------------- #
# Entropía y puntaje
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("length", "pool_size", "expected"),
    [(10, 2, 10.0), (8, 26, 37.6), (0, 26, 0.0), (10, 1, 0.0), (10, 0, 0.0)],
)
def test_calculate_entropy(length, pool_size, expected):
    # Act
    entropy = svc.calculate_entropy(length, pool_size)

    # Assert
    assert entropy == expected


@pytest.mark.parametrize(
    ("entropy", "expected_score"),
    [(0, 0), (27.9, 0), (28, 1), (35.9, 1), (36, 2), (59.9, 2), (60, 3),
     (127.9, 3), (128, 4), (500, 4)],
)
def test_score_from_entropy_uses_thresholds(entropy, expected_score):
    # Act / Assert
    assert svc.score_from_entropy(entropy) == expected_score


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("abc", 26),
        ("ABC", 26),
        ("123", 10),
        ("!!", 32),
        ("ñ", 32),  # caracteres no ASCII se cuentan como símbolos
        ("aB3$", 26 + 26 + 10 + 32),
        ("", 0),
    ],
)
def test_estimate_pool_size(password, expected):
    # Act / Assert
    assert svc.estimate_pool_size(password) == expected


@pytest.mark.parametrize(
    ("password", "expected"), [("aaa", True), ("xx111y", True), ("aabba", False)]
)
def test_has_repeated_characters(password, expected):
    assert svc.has_repeated_characters(password) is expected


@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("xabcx", True),
        ("x987x", True),
        ("CBA", True),
        ("a1b2c3", False),
        ("a-b-c", False),  # contiene símbolos: no es una secuencia
        ("ab", False),  # más corta que la secuencia mínima
    ],
)
def test_has_sequential_characters(password, expected):
    assert svc.has_sequential_characters(password) is expected


# --------------------------------------------------------------------------- #
# Evaluación de fortaleza
# --------------------------------------------------------------------------- #
def test_evaluate_strength_common_password_is_very_weak():
    # Act
    result = svc.evaluate_strength("Password")

    # Assert
    assert result.score == 0
    assert result.label == "muy débil"
    assert "muy común" in result.feedback[0]


def test_evaluate_strength_strong_password_has_no_feedback():
    # Arrange: 20 caracteres variados, sin repeticiones ni secuencias.
    password = "Tq8!vZ#m2Lp@Xw9$Kd4&"

    # Act
    result = svc.evaluate_strength(password)

    # Assert
    assert result.score == 4
    assert result.label == "muy fuerte"
    assert result.feedback == []


def test_evaluate_strength_penalizes_weak_patterns():
    # Arrange: corta, con repetición, secuencia y sin variedad.
    password = "aaaxyz"

    # Act
    result = svc.evaluate_strength(password)

    # Assert
    assert result.score == 0  # el puntaje nunca baja de 0
    assert len(result.feedback) == 4


def test_strength_of_generated_uses_exact_pool():
    # Arrange: solo dígitos -> alfabeto de 10 caracteres.
    options = PasswordOptions(
        length=10, include_lowercase=False, include_uppercase=False,
        include_symbols=False,
    )

    # Act
    result = svc.strength_of_generated(options)

    # Assert
    assert result.entropy_bits == svc.calculate_entropy(10, 10)
    assert result.label == svc.STRENGTH_LABELS[result.score]
    assert result.feedback == []


def test_strength_result_to_dict():
    # Arrange
    result = svc.StrengthResult(score=2, label="aceptable", entropy_bits=40.0)

    # Act / Assert
    assert result.to_dict() == {
        "score": 2, "label": "aceptable", "entropy_bits": 40.0, "feedback": [],
    }


def test_get_password_policy_describes_limits():
    # Act
    policy = svc.get_password_policy()

    # Assert
    assert policy["length"] == {"min": 8, "max": 128, "default": 16}
    assert policy["exclude_ambiguous"]["characters"] == "".join(
        sorted(svc.AMBIGUOUS_CHARACTERS)
    )
    assert policy["strength_labels"] == list(svc.STRENGTH_LABELS)
