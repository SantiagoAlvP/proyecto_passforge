"""Pruebas de ACEPTACIÓN de PassForge con Selenium.

Simulan a una persona usando la aplicación en un navegador real (Chrome sin
ventana), contra la app COMPLETA en ejecución: el frontend (nginx) y el backend
(Flask + Gunicorn), cada uno en su contenedor Docker. Cada prueba recorre un
flujo de usuario y verifica lo que se ve en la página.

Los elementos se localizan con atributos ``data-testid``, que no cambian
aunque cambie el diseño de la página.
"""

import string

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

pytestmark = pytest.mark.acceptance

WAIT_SECONDS = 10

CHARSET_TESTIDS = (
    "include-lowercase",
    "include-uppercase",
    "include-digits",
    "include-symbols",
)


# --------------------------------------------------------------------------- #
# Funciones de ayuda
# --------------------------------------------------------------------------- #
def by_testid(testid):
    """Localizador por atributo data-testid."""
    return (By.CSS_SELECTOR, f"[data-testid='{testid}']")


def find(browser, testid):
    return browser.find_element(*by_testid(testid))


def wait_visible_text(browser, testid):
    """Espera a que el elemento sea visible y devuelve su texto."""
    element = WebDriverWait(browser, WAIT_SECONDS).until(
        EC.visibility_of_element_located(by_testid(testid))
    )
    return element.text


def generate(browser):
    """Pulsa 'Generar contraseña' y devuelve la contraseña mostrada."""
    find(browser, "generate-button").click()
    WebDriverWait(browser, WAIT_SECONDS).until(
        lambda driver: find(driver, "password-output").get_attribute("data-empty")
        == "false"
    )
    return find(browser, "password-output").text


def set_length(browser, length):
    """Mueve el control deslizante de longitud, como lo haría el usuario."""
    slider = find(browser, "length-input")
    browser.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
        slider,
        length,
    )


def check_strength(browser, password):
    """Escribe una contraseña en el comprobador y pulsa 'Comprobar'."""
    field = find(browser, "check-input")
    field.clear()
    field.send_keys(password)
    find(browser, "check-button").click()
    return wait_visible_text(browser, "check-strength")


# --------------------------------------------------------------------------- #
# Historias de usuario
# --------------------------------------------------------------------------- #
class TestHomePage:
    def test_page_loads_and_connects_to_the_server(self, page):
        # Assert: el título y el indicador de conexión con el backend
        assert "PassForge" in page.title
        status = find(page, "api-status")
        assert status.get_attribute("data-state") == "online"
        assert status.text == "Servidor conectado"


class TestGeneratePassword:
    def test_generate_password_with_default_options(self, page):
        # Act
        password = generate(page)

        # Assert: 16 caracteres (valor por defecto) y fortaleza "Fuerte"
        assert len(password) == 16
        assert wait_visible_text(page, "generated-strength").startswith("Fuerte")
        assert find(page, "copy-button").is_enabled()

    def test_generate_long_password_without_symbols(self, page):
        # Arrange: 32 caracteres y sin símbolos
        set_length(page, 32)
        find(page, "include-symbols").click()

        # Act
        password = generate(page)

        # Assert
        assert find(page, "length-value").text == "32"
        assert len(password) == 32
        assert set(password) <= set(string.ascii_letters + string.digits)

    def test_each_click_generates_a_different_password(self, page):
        first = generate(page)

        find(page, "generate-button").click()
        WebDriverWait(page, WAIT_SECONDS).until(
            lambda driver: find(driver, "password-output").text != first
        )

        assert find(page, "password-output").text != first

    def test_shows_an_error_when_no_character_type_is_selected(self, page):
        # Arrange: el usuario desmarca todos los tipos de caracteres
        for testid in CHARSET_TESTIDS:
            find(page, testid).click()

        # Act
        find(page, "generate-button").click()

        # Assert
        error = wait_visible_text(page, "generator-error")
        assert error == "Selecciona al menos un tipo de carácter."


class TestCheckPasswordStrength:
    @pytest.mark.parametrize(
        ("password", "expected_label"),
        [
            ("123456", "Muy débil"),
            ("Kp9#Wm", "Aceptable"),
            ("T7#qL!m9$zR2@vX8", "Fuerte"),
        ],
        ids=["common", "short", "strong"],
    )
    def test_shows_the_strength_level(self, page, password, expected_label):
        # Act
        result = check_strength(page, password)

        # Assert
        assert result.startswith(expected_label)

    def test_weak_password_receives_advice(self, page):
        check_strength(page, "abc")

        feedback = wait_visible_text(page, "check-feedback")

        assert "Usa al menos 12 caracteres." in feedback

    def test_shows_an_error_when_the_field_is_empty(self, page):
        find(page, "check-button").click()

        error = wait_visible_text(page, "checker-error")

        assert error == "Escribe una contraseña para comprobarla."

    def test_show_and_hide_the_typed_password(self, page):
        # Arrange
        field = find(page, "check-input")
        field.send_keys("MiClave#2026")
        toggle = page.find_element(By.ID, "toggle-visibility")

        # Act / Assert: mostrar
        toggle.click()
        assert field.get_attribute("type") == "text"
        assert toggle.text == "Ocultar"

        # Act / Assert: ocultar de nuevo
        toggle.click()
        assert field.get_attribute("type") == "password"
        assert toggle.text == "Mostrar"
