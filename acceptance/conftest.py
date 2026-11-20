"""Configuración compartida de las pruebas de aceptación.

Las pruebas necesitan la aplicación COMPLETA en ejecución:

    docker compose up --build -d        (frontend en :8080, backend en :8000)
    pytest acceptance

La URL del frontend se puede cambiar con la variable de entorno APP_BASE_URL.
"""

import os
import re
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8080")
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
WAIT_SECONDS = 10


@pytest.fixture
def browser():
    """Un Chrome headless (sin ventana) nuevo para cada prueba."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")  # necesario en algunos entornos de CI
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1000")

    # Selenium Manager descarga el driver compatible automáticamente. Si se
    # define CHROMEDRIVER_PATH, se usa ese driver (útil sin acceso a internet).
    driver_path = os.environ.get("CHROMEDRIVER_PATH")
    service = Service(executable_path=driver_path) if driver_path else Service()

    driver = webdriver.Chrome(options=options, service=service)
    yield driver
    driver.quit()


@pytest.fixture
def page(browser):
    """Abre PassForge y espera a que termine de conectarse con el backend."""
    browser.get(APP_BASE_URL)
    WebDriverWait(browser, WAIT_SECONDS).until(
        lambda driver: driver.find_element("tag name", "body").get_attribute(
            "data-ready"
        )
        == "true"
    )
    return browser


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):  # pylint: disable=unused-argument
    """Si una prueba falla, guarda una captura de pantalla del navegador."""
    outcome = yield
    report = outcome.get_result()
    driver = item.funcargs.get("browser") if hasattr(item, "funcargs") else None
    if report.when == "call" and report.failed and driver is not None:
        SCREENSHOTS_DIR.mkdir(exist_ok=True)
        safe_name = re.sub(r"[^\w.-]", "_", item.name)
        driver.save_screenshot(str(SCREENSHOTS_DIR / f"{safe_name}.png"))
