"""Pruebas contra un ambiente desplegado de PassForge (staging o producción).

Se ejecutan desde el pipeline de CD, después de cada despliegue, a través del
ALB (igual que un usuario real). Solo usan la librería estándar de Python.

Niveles:
    preprod   Pruebas completas en staging, antes de promover a producción:
              frontend, enrutamiento del ALB, funcionalidad, validación y
              cabeceras de seguridad.
    postprod  Pruebas de humo en producción: rápidas y livianas, solo
              confirman que el despliegue quedó funcionando.

Uso:
    python scripts/smoke_test.py http://<alb> --level preprod
    python scripts/smoke_test.py http://<alb> --level postprod
    python scripts/smoke_test.py http://<alb> --level postprod --simulate-failure
    python scripts/smoke_test.py http://<alb> --level preprod --expected-version <sha>

Con --expected-version, primero se espera a que /api/v1/health informe esa
versión (APP_VERSION) y se agrega una prueba que lo confirma: así las pruebas
nunca validan, por error, la versión que estaba desplegada antes.
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable

TIMEOUT_SECONDS = 10
WAIT_FOR_HEALTHY_SECONDS = 180
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"


class CheckFailed(AssertionError):
    """Una verificación no se cumplió."""


def request(
    base_url: str, path: str, method: str = "GET", body: dict | None = None
) -> tuple[int, dict[str, str], str]:
    """Hace una petición HTTP y devuelve (status, cabeceras, cuerpo)."""
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        base_url + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8")
    except urllib.error.HTTPError as err:  # 4xx / 5xx también se analizan
        return err.code, dict(err.headers), err.read().decode("utf-8")


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def get_json(base_url: str, path: str, method: str = "GET", body: dict | None = None):
    status, headers, text = request(base_url, path, method, body)
    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"{path} no devolvió JSON (status {status})") from exc
    return status, headers, payload


# --- Verificaciones -----------------------------------------------------------


def check_frontend_loads(base_url: str) -> None:
    status, headers, html = request(base_url, "/")
    expect(status == 200, f"GET / respondió {status}")
    expect("PassForge" in html, "la página principal no contiene 'PassForge'")


def check_api_health(base_url: str) -> None:
    status, _, payload = get_json(base_url, "/api/v1/health")
    expect(status == 200, f"health respondió {status}")
    expect(payload.get("status") == "ok", f"health devolvió {payload}")


def check_deployed_version(base_url: str, expected_version: str) -> None:
    status, _, payload = get_json(base_url, "/api/v1/health")
    expect(status == 200, f"health respondió {status}")
    deployed = payload.get("version")
    expect(
        deployed == expected_version,
        f"versión desplegada {deployed!r}, se esperaba {expected_version!r}",
    )


def check_generate_default(base_url: str) -> None:
    status, _, payload = get_json(base_url, "/api/v1/passwords/generate", "POST", {})
    expect(status == 200, f"generate respondió {status}")
    expect(len(payload.get("password", "")) == 16, "la longitud por defecto no es 16")


def check_frontend_assets(base_url: str) -> None:
    status, headers, _ = request(base_url, "/js/config.js")
    expect(status == 200, f"GET /js/config.js respondió {status}")
    content_type = headers.get("Content-Type", "")
    expect("javascript" in content_type, f"config.js se sirve como {content_type!r}")


def check_alb_routes_api_to_backend(base_url: str) -> None:
    # Una ruta /api/* inexistente debe responderla Flask (JSON), no nginx (HTML)
    status, _, payload = get_json(base_url, "/api/v1/ruta-inexistente")
    expect(status == 404, f"ruta inexistente respondió {status}")
    expect(payload["error"]["code"] == "not_found", f"error inesperado: {payload}")


def check_password_options(base_url: str) -> None:
    status, _, payload = get_json(base_url, "/api/v1/passwords/options")
    expect(status == 200, f"options respondió {status}")
    expect(payload["length"]["min"] == 8, "longitud mínima distinta de 8")
    expect(payload["length"]["max"] == 128, "longitud máxima distinta de 128")


def check_generate_custom(base_url: str) -> None:
    status, _, payload = get_json(
        base_url,
        "/api/v1/passwords/generate",
        "POST",
        {"length": 32, "include_symbols": False},
    )
    expect(status == 200, f"generate respondió {status}")
    password = payload["password"]
    expect(len(password) == 32, f"se pidió longitud 32 y llegó {len(password)}")
    expect(not any(c in SYMBOLS for c in password), "contiene símbolos sin pedirlos")


def check_strength_weak_password(base_url: str) -> None:
    status, _, payload = get_json(
        base_url, "/api/v1/passwords/strength", "POST", {"password": "abc123"}
    )
    expect(status == 200, f"strength respondió {status}")
    expect(payload["score"] == 0, f"'abc123' obtuvo score {payload['score']}")


def check_validation_error(base_url: str) -> None:
    status, _, payload = get_json(
        base_url, "/api/v1/passwords/generate", "POST", {"length": 4}
    )
    expect(status == 400, f"longitud inválida respondió {status}")
    expect(payload["error"]["code"] == "validation_error", f"error: {payload}")


def check_security_headers(base_url: str) -> None:
    _, headers, _ = request(base_url, "/api/v1/health")
    expect(headers.get("X-Content-Type-Options") == "nosniff", "falta nosniff")
    expect(headers.get("Cache-Control") == "no-store", "falta Cache-Control no-store")
    expect(headers.get("X-Frame-Options") == "DENY", "falta X-Frame-Options")


def check_simulated_failure(_: str) -> None:
    raise CheckFailed("falla simulada a propósito para demostrar el rollback")


POSTPROD_CHECKS: list[tuple[str, Callable[[str], None]]] = [
    ("Frontend carga (GET /)", check_frontend_loads),
    ("Backend sano (GET /api/v1/health)", check_api_health),
    ("Genera contraseña por defecto", check_generate_default),
]

PREPROD_CHECKS: list[tuple[str, Callable[[str], None]]] = POSTPROD_CHECKS + [
    ("Frontend sirve JS con MIME correcto", check_frontend_assets),
    ("ALB enruta /api/* al backend", check_alb_routes_api_to_backend),
    ("Política de contraseñas", check_password_options),
    ("Genera contraseña personalizada", check_generate_custom),
    ("Evalúa una contraseña débil", check_strength_weak_password),
    ("Rechaza datos inválidos (400)", check_validation_error),
    ("Cabeceras de seguridad", check_security_headers),
]


def wait_until_healthy(base_url: str, expected_version: str | None = None) -> None:
    """Espera a que el ALB responda (justo después de desplegar puede tardar).

    Si se indica expected_version, espera además a que el backend la informe.
    """
    deadline = time.monotonic() + WAIT_FOR_HEALTHY_SECONDS
    while True:
        try:
            check_api_health(base_url)
            check_frontend_loads(base_url)
            if expected_version:
                check_deployed_version(base_url, expected_version)
            return
        except (CheckFailed, OSError) as exc:
            if time.monotonic() > deadline:
                raise CheckFailed(f"el ambiente no respondió a tiempo: {exc}") from exc
            print(f"  esperando a que el ambiente responda... ({exc})")
            time.sleep(10)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base_url", help="URL del ambiente, p. ej. http://<alb>")
    parser.add_argument("--level", choices=["preprod", "postprod"], required=True)
    parser.add_argument(
        "--simulate-failure",
        action="store_true",
        help="Agrega una prueba que falla (para demostrar el rollback)",
    )
    parser.add_argument(
        "--expected-version",
        help="Versión (SHA) que debe informar /api/v1/health",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    checks = list(PREPROD_CHECKS if args.level == "preprod" else POSTPROD_CHECKS)
    if args.expected_version:
        checks.insert(
            2,
            (
                f"Versión desplegada = {args.expected_version[:7]}",
                functools.partial(
                    check_deployed_version, expected_version=args.expected_version
                ),
            ),
        )
    if args.simulate_failure:
        checks.append(("Falla simulada", check_simulated_failure))

    print(f"Pruebas {args.level} contra {base_url}")
    try:
        wait_until_healthy(base_url, args.expected_version)
    except CheckFailed as exc:
        print(f"  [FALLA] {exc}")
        return 1

    failures = 0
    for name, check in checks:
        try:
            check(base_url)
            print(f"  [OK]    {name}")
        except (CheckFailed, OSError, KeyError) as exc:
            failures += 1
            print(f"  [FALLA] {name}: {exc}")

    total = len(checks)
    print(f"\n{total - failures}/{total} pruebas pasaron")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
