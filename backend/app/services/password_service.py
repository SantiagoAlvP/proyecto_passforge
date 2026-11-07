"""Lógica de negocio para generar y evaluar contraseñas.

Este módulo NO depende de Flask: solo contiene funciones y estructuras de
datos puras. Eso lo hace fácil de reutilizar y de probar de forma aislada.

Seguridad: para generar contraseñas se usa el módulo ``secrets`` (generador
criptográficamente seguro del sistema operativo) y NUNCA ``random``, cuyo
generador es predecible y no apto para fines de seguridad.
"""

from __future__ import annotations

import math
import re
import secrets
import string
from dataclasses import asdict, dataclass, field
from typing import Any

# --------------------------------------------------------------------------- #
# Constantes de la política de contraseñas
# --------------------------------------------------------------------------- #
MIN_LENGTH = 8
MAX_LENGTH = 128
DEFAULT_LENGTH = 16

#: Longitud máxima aceptada al evaluar una contraseña escrita por el usuario.
MAX_PASSWORD_INPUT_LENGTH = 128

LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
DIGITS = string.digits
# Símbolos "seguros": se excluyen comillas, barra invertida y espacios porque
# suelen causar problemas al pegarlos en formularios, shells o archivos.
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"
#: Caracteres que se confunden fácilmente a simple vista.
AMBIGUOUS_CHARACTERS = frozenset("Il1O0o")

#: Umbrales de entropía (bits) para cada nivel. Son los rangos usados por
#: herramientas como KeePass: < 28 muy débil, < 36 débil, < 60 aceptable,
#: < 128 fuerte y >= 128 muy fuerte.
_ENTROPY_THRESHOLDS = (28, 36, 60, 128)
STRENGTH_LABELS = ("muy débil", "débil", "aceptable", "fuerte", "muy fuerte")
MAX_SCORE = len(STRENGTH_LABELS) - 1

#: Pequeña muestra de contraseñas muy comunes. En un sistema real se usaría
#: una lista mucho más grande o un servicio como "Have I Been Pwned".
COMMON_PASSWORDS = frozenset(
    {
        "123456",
        "12345678",
        "123456789",
        "1234567890",
        "111111",
        "000000",
        "password",
        "password1",
        "qwerty",
        "qwerty123",
        "abc123",
        "letmein",
        "iloveyou",
        "admin",
        "welcome",
        "monkey",
        "dragon",
        "contraseña",
        "contrasena",
        "teamo",
    }
)

_SECURE_RANDOM = secrets.SystemRandom()
_FULL_POOL_SIZE = len(LOWERCASE) + len(UPPERCASE) + len(DIGITS) + len(string.punctuation)
_REPEATED_CHARS_PATTERN = re.compile(r"(.)\1\1")


# --------------------------------------------------------------------------- #
# Estructuras de datos
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PasswordOptions:
    """Opciones para generar una contraseña.

    Es inmutable (``frozen``) y valida sus propios invariantes al crearse,
    de modo que nunca puede existir un objeto ``PasswordOptions`` inválido.
    """

    length: int = DEFAULT_LENGTH
    include_lowercase: bool = True
    include_uppercase: bool = True
    include_digits: bool = True
    include_symbols: bool = True
    exclude_ambiguous: bool = False

    def __post_init__(self) -> None:
        if not MIN_LENGTH <= self.length <= MAX_LENGTH:
            raise ValueError(
                f"La longitud debe estar entre {MIN_LENGTH} y {MAX_LENGTH}."
            )
        if not any(
            (
                self.include_lowercase,
                self.include_uppercase,
                self.include_digits,
                self.include_symbols,
            )
        ):
            raise ValueError("Debe seleccionarse al menos un tipo de carácter.")


@dataclass(frozen=True)
class StrengthResult:
    """Resultado de evaluar la fortaleza de una contraseña."""

    score: int
    label: str
    entropy_bits: float
    feedback: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Generación
# --------------------------------------------------------------------------- #
def build_character_sets(options: PasswordOptions) -> list[str]:
    """Devuelve los conjuntos de caracteres seleccionados en ``options``."""
    selected = [
        (options.include_lowercase, LOWERCASE),
        (options.include_uppercase, UPPERCASE),
        (options.include_digits, DIGITS),
        (options.include_symbols, SYMBOLS),
    ]
    charsets = [chars for enabled, chars in selected if enabled]

    if options.exclude_ambiguous:
        charsets = [
            "".join(ch for ch in chars if ch not in AMBIGUOUS_CHARACTERS)
            for chars in charsets
        ]
    return charsets


def generate_password(options: PasswordOptions) -> str:
    """Genera una contraseña aleatoria segura según ``options``.

    Garantiza que la contraseña contenga al menos un carácter de cada
    conjunto seleccionado y luego mezcla el resultado para que esos
    caracteres no queden siempre al principio.
    """
    charsets = build_character_sets(options)
    pool = "".join(charsets)

    # Un carácter obligatorio por cada conjunto seleccionado...
    characters = [secrets.choice(chars) for chars in charsets]
    # ...y el resto, elegidos del conjunto completo.
    remaining = options.length - len(characters)
    characters.extend(secrets.choice(pool) for _ in range(remaining))

    _SECURE_RANDOM.shuffle(characters)
    return "".join(characters)


# --------------------------------------------------------------------------- #
# Evaluación de fortaleza
# --------------------------------------------------------------------------- #
def calculate_entropy(length: int, pool_size: int) -> float:
    """Entropía en bits: ``length * log2(pool_size)``.

    Representa cuántos intentos (2^bits) necesitaría, en promedio, un ataque
    de fuerza bruta. Devuelve 0 si no hay longitud o el alfabeto es trivial.
    """
    if length <= 0 or pool_size <= 1:
        return 0.0
    return round(length * math.log2(pool_size), 2)


def score_from_entropy(entropy_bits: float) -> int:
    """Convierte bits de entropía en un puntaje de 0 (muy débil) a 4."""
    for score, threshold in enumerate(_ENTROPY_THRESHOLDS):
        if entropy_bits < threshold:
            return score
    return MAX_SCORE


def estimate_pool_size(password: str) -> int:
    """Estima el tamaño del alfabeto según los tipos de caracteres usados."""
    pool_size = 0
    if any(ch in LOWERCASE for ch in password):
        pool_size += len(LOWERCASE)
    if any(ch in UPPERCASE for ch in password):
        pool_size += len(UPPERCASE)
    if any(ch in DIGITS for ch in password):
        pool_size += len(DIGITS)
    if any(not ch.isascii() or not ch.isalnum() for ch in password):
        pool_size += len(string.punctuation)
    return pool_size


def has_repeated_characters(password: str) -> bool:
    """``True`` si hay 3 o más caracteres iguales seguidos (ej. ``aaa``)."""
    return _REPEATED_CHARS_PATTERN.search(password) is not None


def has_sequential_characters(password: str, run: int = 3) -> bool:
    """``True`` si hay una secuencia de ``run`` caracteres consecutivos.

    Detecta secuencias ascendentes o descendentes de letras o números,
    como ``abc``, ``123``, ``cba`` o ``987`` (sin distinguir mayúsculas).
    """
    text = password.lower()
    for start in range(len(text) - run + 1):
        chunk = text[start : start + run]
        if not (chunk.isascii() and chunk.isalnum()):
            continue
        steps = {ord(b) - ord(a) for a, b in zip(chunk, chunk[1:])}
        if steps in ({1}, {-1}):
            return True
    return False


def evaluate_strength(password: str) -> StrengthResult:
    """Evalúa una contraseña escrita por el usuario.

    Combina la entropía estimada con penalizaciones por patrones débiles
    (contraseñas comunes, repeticiones y secuencias) y devuelve consejos.
    """
    entropy = calculate_entropy(len(password), estimate_pool_size(password))

    if password.lower() in COMMON_PASSWORDS:
        return StrengthResult(
            score=0,
            label=STRENGTH_LABELS[0],
            entropy_bits=entropy,
            feedback=["Es una contraseña muy común y fácil de adivinar."],
        )

    score = score_from_entropy(entropy)
    feedback: list[str] = []

    if has_repeated_characters(password):
        score -= 1
        feedback.append("Evita repetir el mismo carácter varias veces seguidas.")
    if has_sequential_characters(password):
        score -= 1
        feedback.append("Evita secuencias predecibles como 'abc' o '123'.")
    if len(password) < 12:
        feedback.append("Usa al menos 12 caracteres.")
    if estimate_pool_size(password) < _FULL_POOL_SIZE:
        feedback.append("Combina mayúsculas, minúsculas, números y símbolos.")

    score = max(score, 0)
    return StrengthResult(
        score=score,
        label=STRENGTH_LABELS[score],
        entropy_bits=entropy,
        feedback=feedback,
    )


def strength_of_generated(options: PasswordOptions) -> StrengthResult:
    """Fortaleza de una contraseña generada con ``options``.

    Como el alfabeto es conocido exactamente, la entropía se calcula sobre
    él (y no estimando a partir del texto), lo que es más preciso.
    """
    pool_size = len("".join(build_character_sets(options)))
    entropy = calculate_entropy(options.length, pool_size)
    score = score_from_entropy(entropy)
    return StrengthResult(
        score=score, label=STRENGTH_LABELS[score], entropy_bits=entropy
    )


def get_password_policy() -> dict[str, Any]:
    """Describe las opciones admitidas, para que el frontend arme su UI."""
    return {
        "length": {
            "min": MIN_LENGTH,
            "max": MAX_LENGTH,
            "default": DEFAULT_LENGTH,
        },
        "character_sets": {
            "include_lowercase": {"default": True, "characters": LOWERCASE},
            "include_uppercase": {"default": True, "characters": UPPERCASE},
            "include_digits": {"default": True, "characters": DIGITS},
            "include_symbols": {"default": True, "characters": SYMBOLS},
        },
        "exclude_ambiguous": {
            "default": False,
            "characters": "".join(sorted(AMBIGUOUS_CHARACTERS)),
        },
        "max_password_input_length": MAX_PASSWORD_INPUT_LENGTH,
        "strength_labels": list(STRENGTH_LABELS),
    }
