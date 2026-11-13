"""Pruebas UNITARIAS de app/services/password_service.py

Cada prueba ejecuta UNA función o clase del servicio, de forma aislada: sin
Flask, sin servidor y sin red. Cuando el resultado depende del azar, el azar
se reemplaza por un "doble de prueba" con ``monkeypatch``.

Todas siguen la estrategia AAA:
    # Arrange -> preparar los datos de entrada
    # Act     -> ejecutar UNA acción: la función que se prueba
    # Assert  -> verificar que el resultado es el esperado
"""

import string

import pytest

from app.services import password_service
from app.services.password_service import (
    AMBIGUOUS_CHARACTERS,
    DIGITS,
    LOWERCASE,
    SYMBOLS,
    UPPERCASE,
    PasswordOptions,
    StrengthResult,
    build_character_sets,
    calculate_entropy,
    estimate_pool_size,
    evaluate_strength,
    generate_password,
    get_password_policy,
    has_repeated_characters,
    has_sequential_characters,
    score_from_entropy,
    strength_of_generated,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# generate_password
# --------------------------------------------------------------------------- #
def test_generate_password_has_requested_length():
    # Arrange: prepara los datos de entrada
    options = PasswordOptions(length=20)

    # Act: ejecuta la función que estás probando
    password = generate_password(options)

    # Assert: verifica el resultado
    assert len(password) == 20


class TestGeneratePassword:
    @pytest.mark.parametrize("length", [8, 128])
    def test_password_length_at_the_limits(self, length):
        # Arrange: valores límite (mínimo y máximo permitidos)
        options = PasswordOptions(length=length)

        # Act
        password = generate_password(options)

        # Assert
        assert len(password) == length

    def test_password_contains_at_least_one_character_of_each_selected_set(self):
        # Arrange: longitud mínima = el caso más difícil de cumplir
        options = PasswordOptions(length=8)

        # Act
        password = generate_password(options)

        # Assert
        assert any(ch in LOWERCASE for ch in password)
        assert any(ch in UPPERCASE for ch in password)
        assert any(ch in DIGITS for ch in password)
        assert any(ch in SYMBOLS for ch in password)

    def test_password_with_only_digits_contains_only_digits(self):
        # Arrange
        options = PasswordOptions(
            length=32,
            include_lowercase=False,
            include_uppercase=False,
            include_symbols=False,
        )

        # Act
        password = generate_password(options)

        # Assert
        assert password.isdigit()

    def test_password_excludes_ambiguous_characters_when_requested(self):
        # Arrange: una contraseña larga hace muy probable que aparecieran
        options = PasswordOptions(length=128, exclude_ambiguous=True)

        # Act
        password = generate_password(options)

        # Assert
        assert set(password).isdisjoint(AMBIGUOUS_CHARACTERS)

    def test_two_generated_passwords_are_different(self):
        # Arrange
        options = PasswordOptions()

        # Act
        first = generate_password(options)
        second = generate_password(options)

        # Assert
        assert first != second

    def test_result_is_predictable_when_randomness_is_replaced(self, monkeypatch):
        """AISLAMIENTO: se reemplaza la aleatoriedad por una fuente predecible
        (un "doble de prueba") para verificar la lógica exacta."""
        # Arrange: choice() devuelve siempre el primer carácter y
        # shuffle() no mezcla nada.
        monkeypatch.setattr(password_service.secrets, "choice", lambda chars: chars[0])
        monkeypatch.setattr(password_service._SECURE_RANDOM, "shuffle", lambda items: None)
        options = PasswordOptions(length=8)

        # Act
        password = generate_password(options)

        # Assert: 1 obligatorio por conjunto (a, A, 0, !) + relleno con "a"
        assert password == "aA0!aaaa"

    def test_characters_are_shuffled_with_the_secure_generator(self, monkeypatch):
        # Arrange: un "espía" que registra las llamadas a shuffle()
        calls = []
        monkeypatch.setattr(
            password_service._SECURE_RANDOM, "shuffle", lambda items: calls.append(items)
        )

        # Act
        generate_password(PasswordOptions(length=10))

        # Assert
        assert len(calls) == 1
        assert len(calls[0]) == 10


# --------------------------------------------------------------------------- #
# PasswordOptions
# --------------------------------------------------------------------------- #
class TestPasswordOptions:
    def test_default_options(self):
        # Act
        options = PasswordOptions()

        # Assert
        assert options.length == 16
        assert options.include_lowercase is True
        assert options.include_uppercase is True
        assert options.include_digits is True
        assert options.include_symbols is True
        assert options.exclude_ambiguous is False

    @pytest.mark.parametrize("invalid_length", [7, 129])
    def test_rejects_length_out_of_range(self, invalid_length):
        with pytest.raises(ValueError, match="longitud"):
            PasswordOptions(length=invalid_length)

    def test_rejects_options_without_any_character_set(self):
        with pytest.raises(ValueError, match="al menos un tipo"):
            PasswordOptions(
                include_lowercase=False,
                include_uppercase=False,
                include_digits=False,
                include_symbols=False,
            )

    def test_options_are_immutable(self):
        # Arrange
        options = PasswordOptions()

        # Act / Assert: frozen=True impide modificarlas después de validarlas
        with pytest.raises(AttributeError):
            options.length = 4


# --------------------------------------------------------------------------- #
# build_character_sets
# --------------------------------------------------------------------------- #
class TestBuildCharacterSets:
    def test_returns_only_the_selected_sets(self):
        # Arrange
        options = PasswordOptions(include_uppercase=False, include_symbols=False)

        # Act
        charsets = build_character_sets(options)

        # Assert
        assert charsets == [LOWERCASE, DIGITS]

    def test_removes_ambiguous_characters_when_requested(self):
        # Arrange
        options = PasswordOptions(exclude_ambiguous=True)

        # Act
        charsets = build_character_sets(options)

        # Assert
        assert set("".join(charsets)).isdisjoint(AMBIGUOUS_CHARACTERS)


# --------------------------------------------------------------------------- #
# calculate_entropy y score_from_entropy
# --------------------------------------------------------------------------- #
class TestEntropy:
    @pytest.mark.parametrize(
        ("length", "pool_size", "expected_bits"),
        [
            (16, 86, 102.82),  # 16 caracteres, todos los conjuntos
            (8, 10, 26.58),  # PIN de 8 dígitos
            (0, 94, 0.0),  # contraseña vacía
            (10, 1, 0.0),  # alfabeto de un solo carácter
        ],
    )
    def test_calculate_entropy(self, length, pool_size, expected_bits):
        assert calculate_entropy(length, pool_size) == expected_bits

    @pytest.mark.parametrize(
        ("entropy_bits", "expected_score"),
        [
            (0, 0),
            (27.99, 0),
            (28, 1),  # límites exactos entre niveles
            (36, 2),
            (60, 3),
            (127.99, 3),
            (128, 4),
            (500, 4),
        ],
    )
    def test_score_from_entropy(self, entropy_bits, expected_score):
        assert score_from_entropy(entropy_bits) == expected_score


# --------------------------------------------------------------------------- #
# Detección de patrones
# --------------------------------------------------------------------------- #
class TestPatterns:
    @pytest.mark.parametrize(
        ("password", "expected_pool"),
        [
            ("abc", 26),
            ("ABC", 26),
            ("123", 10),
            ("!?", 32),
            ("aB3", 62),
            ("aB3!", 94),
            ("ñ", 32),  # caracteres no ASCII cuentan como símbolos
        ],
    )
    def test_estimate_pool_size(self, password, expected_pool):
        assert estimate_pool_size(password) == expected_pool

    @pytest.mark.parametrize(
        ("password", "expected"),
        [("aaa", True), ("x1111y", True), ("aabbcc", False), ("", False)],
    )
    def test_has_repeated_characters(self, password, expected):
        assert has_repeated_characters(password) is expected

    @pytest.mark.parametrize(
        ("password", "expected"),
        [
            ("abc", True),  # ascendente
            ("x789", True),  # números
            ("CBA", True),  # descendente, sin importar mayúsculas
            ("a1b2c3", False),
            ("ab", False),  # muy corta
            ("a-b-c", False),  # separada por símbolos
        ],
    )
    def test_has_sequential_characters(self, password, expected):
        assert has_sequential_characters(password) is expected


# --------------------------------------------------------------------------- #
# evaluate_strength
# --------------------------------------------------------------------------- #
class TestEvaluateStrength:
    def test_common_password_is_very_weak(self):
        # Act
        result = evaluate_strength("123456")

        # Assert
        assert result.score == 0
        assert result.label == "muy débil"
        assert result.feedback == ["Es una contraseña muy común y fácil de adivinar."]

    def test_common_password_detection_ignores_case(self):
        assert evaluate_strength("PassWord").score == 0

    def test_strong_password_has_no_feedback(self):
        # Act
        result = evaluate_strength("T7#qL!m9$zR2@vX8")

        # Assert
        assert result.score == 3
        assert result.label == "fuerte"
        assert result.feedback == []

    def test_short_password_receives_length_advice(self):
        result = evaluate_strength("Kp9#Wm")

        assert "Usa al menos 12 caracteres." in result.feedback

    def test_password_with_one_character_type_receives_mix_advice(self):
        result = evaluate_strength("solominusculasaqui")

        assert "Combina mayúsculas, minúsculas, números y símbolos." in result.feedback

    def test_repeated_characters_lower_the_score(self):
        # Arrange: misma longitud y tipos de caracteres; la segunda repite "qqq"
        good = evaluate_strength("Kp9#Wm2$Lq7!")

        # Act
        repeated = evaluate_strength("Kp9#Wm2$Lqqq")

        # Assert
        assert repeated.score == good.score - 1
        assert "Evita repetir el mismo carácter varias veces seguidas." in repeated.feedback

    def test_sequences_lower_the_score(self):
        good = evaluate_strength("Kp9#Wm2$Lq7!")

        with_sequence = evaluate_strength("Kp9#Wm2$abc!")

        assert with_sequence.score == good.score - 1
        assert "Evita secuencias predecibles como 'abc' o '123'." in with_sequence.feedback

    def test_score_never_goes_below_zero(self):
        # Arrange: ya es "muy débil" y además tiene repetición y secuencia
        result = evaluate_strength("aaabc")

        assert result.score == 0
        assert result.label == "muy débil"


# --------------------------------------------------------------------------- #
# strength_of_generated, StrengthResult y get_password_policy
# --------------------------------------------------------------------------- #
class TestStrengthOfGenerated:
    def test_default_options_are_strong(self):
        result = strength_of_generated(PasswordOptions())

        assert result.entropy_bits == 102.82
        assert result.score == 3
        assert result.label == "fuerte"
        assert result.feedback == []

    def test_excluding_ambiguous_characters_reduces_entropy(self):
        normal = strength_of_generated(PasswordOptions())

        without_ambiguous = strength_of_generated(PasswordOptions(exclude_ambiguous=True))

        assert without_ambiguous.entropy_bits < normal.entropy_bits


class TestStrengthResult:
    def test_to_dict_returns_all_fields(self):
        # Arrange
        result = StrengthResult(score=2, label="aceptable", entropy_bits=40.5, feedback=["x"])

        # Act
        data = result.to_dict()

        # Assert
        assert data == {
            "score": 2,
            "label": "aceptable",
            "entropy_bits": 40.5,
            "feedback": ["x"],
        }


class TestPasswordPolicy:
    def test_policy_exposes_length_limits_and_character_sets(self):
        policy = get_password_policy()

        assert policy["length"] == {"min": 8, "max": 128, "default": 16}
        assert set(policy["character_sets"]) == {
            "include_lowercase",
            "include_uppercase",
            "include_digits",
            "include_symbols",
        }
        assert policy["character_sets"]["include_digits"]["characters"] == string.digits
        assert policy["max_password_input_length"] == 128
