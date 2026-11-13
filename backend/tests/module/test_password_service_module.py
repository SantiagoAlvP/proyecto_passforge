"""Pruebas MODULARES del módulo de contraseñas: app/services/password_service.py

Diferencia con las unitarias:
  - Unitaria: UNA función, aislada; si depende del azar u otra pieza, se
    reemplaza por un doble de prueba.
  - Modular: el MÓDULO COMPLETO a través de su interfaz pública, dejando que
    sus funciones colaboren entre sí de verdad (sin dobles de prueba).

El módulo se prueba independiente del resto del sistema: sin Flask, sin
rutas y sin HTTP.
"""

from collections import Counter
from itertools import combinations

import pytest

from app.services.password_service import (
    PasswordOptions,
    build_character_sets,
    calculate_entropy,
    evaluate_strength,
    generate_password,
    get_password_policy,
    strength_of_generated,
)

pytestmark = pytest.mark.module

CHARSET_FIELDS = ("include_lowercase", "include_uppercase", "include_digits", "include_symbols")
# Las 15 combinaciones posibles de conjuntos de caracteres (1, 2, 3 o 4 a la vez).
ALL_CHARSET_COMBINATIONS = [
    combo for size in range(1, 5) for combo in combinations(CHARSET_FIELDS, size)
]


def options_with(charsets, **kwargs):
    """Crea PasswordOptions activando solo los conjuntos indicados."""
    return PasswordOptions(**{name: name in charsets for name in CHARSET_FIELDS}, **kwargs)


class TestPolicyIsConsistentWithTheModule:
    """Lo que el módulo PUBLICA en su política es lo que realmente HACE."""

    def test_length_limits_published_in_the_policy_are_enforced(self):
        # Arrange
        limits = get_password_policy()["length"]

        # Act / Assert: los límites exactos se aceptan...
        PasswordOptions(length=limits["min"])
        PasswordOptions(length=limits["max"])
        # ...y un valor fuera de ellos se rechaza
        for invalid in (limits["min"] - 1, limits["max"] + 1):
            with pytest.raises(ValueError):
                PasswordOptions(length=invalid)

    def test_default_length_in_the_policy_is_the_real_default(self):
        assert PasswordOptions().length == get_password_policy()["length"]["default"]

    @pytest.mark.parametrize("charset", CHARSET_FIELDS)
    def test_each_published_character_set_is_what_the_generator_uses(self, charset):
        # Arrange
        published = get_password_policy()["character_sets"][charset]["characters"]
        options = options_with({charset}, length=128)

        # Act
        password = generate_password(options)

        # Assert
        assert set(password) <= set(published)

    def test_published_ambiguous_characters_are_excluded(self):
        # Arrange
        ambiguous = get_password_policy()["exclude_ambiguous"]["characters"]

        # Act
        password = generate_password(PasswordOptions(length=128, exclude_ambiguous=True))

        # Assert
        assert set(password).isdisjoint(ambiguous)

    def test_every_label_returned_by_the_module_is_published(self):
        # Arrange
        labels = get_password_policy()["strength_labels"]
        samples = ["123456", "Kp9#W", "Kp9#Wm", "Kp9#Wm2$Lq7!", "T7#qL!m9$zR2@vX8yW4%nB6&"]

        # Act
        results = [evaluate_strength(sample) for sample in samples]

        # Assert: cada etiqueta existe y corresponde a su puntaje
        for result in results:
            assert labels[result.score] == result.label
        # y con estas muestras se recorren todos los niveles
        assert {result.score for result in results} == set(range(len(labels)))


class TestGenerationAndEvaluationWorkTogether:
    @pytest.mark.parametrize(
        "charsets", ALL_CHARSET_COMBINATIONS, ids=lambda c: "+".join(n[8:] for n in c)
    )
    def test_every_combination_uses_all_and_only_the_selected_sets(self, charsets):
        # Arrange
        options = options_with(charsets, length=12)
        selected_sets = dict(zip(CHARSET_FIELDS, build_character_sets(PasswordOptions())))

        # Act
        password = generate_password(options)

        # Assert
        assert len(password) == 12
        for name, characters in selected_sets.items():
            is_present = any(ch in characters for ch in password)
            assert is_present is (name in charsets), name

    def test_generated_passwords_never_need_length_or_composition_advice(self):
        # Act: el propio módulo evalúa 200 contraseñas que él mismo generó
        results = [
            evaluate_strength(generate_password(PasswordOptions(length=16)))
            for _ in range(200)
        ]

        # Assert
        for result in results:
            assert "Usa al menos 12 caracteres." not in result.feedback
            assert "Combina mayúsculas, minúsculas, números y símbolos." not in result.feedback

    @pytest.mark.parametrize("exclude_ambiguous", [False, True])
    def test_reported_strength_matches_the_real_alphabet(self, exclude_ambiguous):
        # Arrange
        options = PasswordOptions(length=20, exclude_ambiguous=exclude_ambiguous)
        alphabet = "".join(build_character_sets(options))

        # Act
        strength = strength_of_generated(options)

        # Assert
        assert strength.entropy_bits == calculate_entropy(20, len(alphabet))


class TestRandomnessQuality:
    def test_no_password_is_repeated_in_a_large_sample(self):
        # Act
        passwords = [generate_password(PasswordOptions()) for _ in range(1000)]

        # Assert
        assert len(set(passwords)) == 1000

    def test_every_character_appears_with_a_similar_frequency(self):
        """Ningún carácter del alfabeto queda excluido ni se favorece demasiado."""
        # Arrange
        options = PasswordOptions(length=128)
        alphabet = "".join(build_character_sets(options))
        samples = 300

        # Act
        counts = Counter("".join(generate_password(options) for _ in range(samples)))

        # Assert: margen amplio (±50 %) para que la prueba no falle por azar
        expected = samples * 128 / len(alphabet)
        assert set(counts) == set(alphabet)
        assert all(0.5 * expected < count < 1.5 * expected for count in counts.values())
