"""Pruebas de aceptación (E2E) con Playwright.

Simulan a un usuario real: levantan el backend y el frontend, abren un
navegador Chromium, hacen clic en la interfaz y verifican lo que se ve en la
página.

Ejecutar (desde ``backend/``)::

    playwright install chromium        # solo la primera vez
    pytest -m e2e                       # navegador oculto
    pytest -m e2e --headed --slowmo 500 # para ver el navegador en acción
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

BACKEND_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"
API_PORT = 8000  # el frontend lo espera en este puerto (frontend/js/config.js)
FRONTEND_PORT = 5500
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"


def _wait_for_port(port: int, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"Nada escucha en el puerto {port} tras {timeout} s.")


def _start(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        command, cwd=cwd, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="session")
def running_app() -> Iterator[str]:
    """Paso 1: inicia la aplicación (backend + frontend) y la apaga al final."""
    env = {**os.environ, "APP_ENV": "testing", "HOST": "127.0.0.1",
           "PORT": str(API_PORT)}
    backend = _start([sys.executable, "wsgi.py"], BACKEND_DIR, env)
    frontend = _start(
        [sys.executable, "-m", "http.server", str(FRONTEND_PORT),
         "--bind", "127.0.0.1"],
        FRONTEND_DIR, env,
    )
    try:
        _wait_for_port(API_PORT)
        _wait_for_port(FRONTEND_PORT)
        yield FRONTEND_URL
    finally:
        for process in (backend, frontend):
            process.terminate()
            process.wait(timeout=10)


def test_user_generates_a_password(running_app: str, page: Page) -> None:
    # Paso 2: abre el navegador en la página principal.
    page.goto(running_app)
    expect(page.get_by_test_id("api-status")).to_have_attribute(
        "data-state", "online"
    )

    # Paso 3: encuentra los controles (longitud y botón «Generar»).
    output = page.get_by_test_id("password-output")
    page.get_by_test_id("length-input").fill("24")
    page.get_by_test_id("include-symbols").uncheck()

    # Paso 4: hace clic en el botón.
    page.get_by_test_id("generate-button").click()

    # Paso 5: verifica (Assert) que la contraseña aparece en la página.
    expect(output).to_have_attribute("data-empty", "false")
    password = output.inner_text()
    assert len(password) == 24
    assert password.isalnum()  # se desmarcaron los símbolos
    expect(page.get_by_test_id("generated-strength")).to_contain_text(
        "bits de entropía"
    )
    expect(page.get_by_test_id("copy-button")).to_be_enabled()


def test_user_checks_a_weak_password(running_app: str, page: Page) -> None:
    # Arrange
    page.goto(running_app)

    # Act: escribe una contraseña común y pulsa «Comprobar».
    page.get_by_test_id("check-input").fill("123456")
    page.get_by_test_id("check-button").click()

    # Assert
    expect(page.get_by_test_id("check-result")).to_be_visible()
    expect(page.get_by_test_id("check-strength")).to_contain_text("Muy débil")
    expect(page.get_by_test_id("check-feedback")).to_contain_text("muy común")
