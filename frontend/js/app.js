/**
 * Lógica de la interfaz de PassForge.
 *
 * Seguridad: todo dato que viene del servidor o del usuario se inserta en la
 * página con `textContent` (nunca con `innerHTML`) para evitar XSS. La
 * contraseña generada solo vive en memoria: no se guarda en localStorage.
 */
import {
  ApiError,
  checkPasswordStrength,
  generatePassword,
  getHealth,
  getPasswordOptions,
} from "./api.js";

const CHARSET_FIELDS = [
  "include_lowercase",
  "include_uppercase",
  "include_digits",
  "include_symbols",
];
const COPY_FEEDBACK_MS = 2000;

const $ = (selector) => document.querySelector(selector);

const ui = {
  apiStatus: $(".api-status"),
  apiStatusText: $(".api-status__text"),
  passwordOutput: $("#password-output"),
  generatedMeter: $("#generated-meter"),
  generatedStrength: $("#generated-strength"),
  copyButton: $("#copy-button"),
  generatorForm: $("#generator-form"),
  generatorError: $("#generator-error"),
  lengthInput: $("#length"),
  lengthValue: $("#length-value"),
  checkerForm: $("#checker-form"),
  checkerError: $("#checker-error"),
  checkInput: $("#check-password"),
  toggleVisibility: $("#toggle-visibility"),
  checkResult: $("#check-result"),
  checkMeter: $("#check-meter"),
  checkStrength: $("#check-strength"),
  checkFeedback: $("#check-feedback"),
};

let currentPassword = "";
let copyResetTimer;

/* ------------------------------------------------------------------ */
/* Presentación                                                        */
/* ------------------------------------------------------------------ */

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function characterKind(character) {
  if (/[0-9]/.test(character)) return "digit";
  if (/[A-Za-z]/.test(character)) return "letter";
  return "symbol";
}

/** Muestra la contraseña con un color distinto por tipo de carácter. */
function renderPassword(password) {
  const spans = Array.from(password, (character) => {
    const span = document.createElement("span");
    span.className = `char char--${characterKind(character)}`;
    span.textContent = character;
    return span;
  });
  ui.passwordOutput.replaceChildren(...spans);
  ui.passwordOutput.dataset.empty = "false";
}

function renderStrength(container, meter, strength) {
  const label = document.createElement("strong");
  label.className = "strength__label";
  label.textContent = capitalize(strength.label);

  const bits = document.createElement("span");
  bits.className = "strength__bits";
  const formatted = strength.entropy_bits.toLocaleString("es", {
    maximumFractionDigits: 1,
  });
  bits.textContent = `${formatted} bits de entropía`;

  container.replaceChildren(label, " ", bits);
  container.dataset.score = String(strength.score);
  meter.dataset.score = String(strength.score);
}

function renderFeedback(items) {
  const messages = items.length ? items : ["No se detectaron patrones débiles."];
  const listItems = messages.map((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    return item;
  });
  ui.checkFeedback.replaceChildren(...listItems);
}

function setApiStatus(state, text) {
  ui.apiStatus.dataset.state = state;
  ui.apiStatusText.textContent = text;
}

function showMessage(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function showError(element, error) {
  if (!(error instanceof ApiError)) {
    console.error(error);
    showMessage(element, "Ocurrió un error inesperado. Recarga la página e inténtalo de nuevo.");
    return;
  }
  const details = Object.values(error.details);
  showMessage(element, [error.message, ...details].join(" "));
}

function clearMessage(element) {
  element.textContent = "";
  element.hidden = true;
}

function setBusy(form, busy) {
  form.setAttribute("aria-busy", String(busy));
  form.querySelector("[type='submit']").disabled = busy;
}

function syncLengthValue() {
  ui.lengthValue.textContent = ui.lengthInput.value;
}

function resetCopyButton() {
  ui.copyButton.textContent = "Copiar";
}

/* ------------------------------------------------------------------ */
/* Acciones del usuario                                                */
/* ------------------------------------------------------------------ */

function readGeneratorOptions() {
  const formData = new FormData(ui.generatorForm);
  const options = { length: Number.parseInt(ui.lengthInput.value, 10) };
  for (const name of [...CHARSET_FIELDS, "exclude_ambiguous"]) {
    options[name] = formData.has(name);
  }
  return options;
}

async function handleGenerate(event) {
  event.preventDefault();
  clearMessage(ui.generatorError);

  const options = readGeneratorOptions();
  if (!CHARSET_FIELDS.some((name) => options[name])) {
    showMessage(ui.generatorError, "Selecciona al menos un tipo de carácter.");
    return;
  }

  setBusy(ui.generatorForm, true);
  try {
    const result = await generatePassword(options);
    currentPassword = result.password;
    renderPassword(result.password);
    renderStrength(ui.generatedStrength, ui.generatedMeter, result.strength);
    ui.copyButton.disabled = false;
    resetCopyButton();
  } catch (error) {
    showError(ui.generatorError, error);
  } finally {
    setBusy(ui.generatorForm, false);
  }
}

async function handleCopy() {
  if (!currentPassword) return;
  try {
    await navigator.clipboard.writeText(currentPassword);
    ui.copyButton.textContent = "Copiada";
  } catch {
    ui.copyButton.textContent = "Cópiala manualmente";
  }
  clearTimeout(copyResetTimer);
  copyResetTimer = setTimeout(resetCopyButton, COPY_FEEDBACK_MS);
}

async function handleCheck(event) {
  event.preventDefault();
  clearMessage(ui.checkerError);

  const password = ui.checkInput.value;
  if (!password) {
    ui.checkResult.hidden = true;
    showMessage(ui.checkerError, "Escribe una contraseña para comprobarla.");
    ui.checkInput.focus();
    return;
  }

  setBusy(ui.checkerForm, true);
  try {
    const result = await checkPasswordStrength(password);
    renderStrength(ui.checkStrength, ui.checkMeter, result);
    renderFeedback(result.feedback);
    ui.checkResult.hidden = false;
  } catch (error) {
    ui.checkResult.hidden = true;
    showError(ui.checkerError, error);
  } finally {
    setBusy(ui.checkerForm, false);
  }
}

function handleToggleVisibility() {
  const reveal = ui.checkInput.type === "password";
  ui.checkInput.type = reveal ? "text" : "password";
  ui.toggleVisibility.textContent = reveal ? "Ocultar" : "Mostrar";
  ui.toggleVisibility.setAttribute("aria-pressed", String(reveal));
}

/* ------------------------------------------------------------------ */
/* Arranque                                                            */
/* ------------------------------------------------------------------ */

/** Ajusta el formulario a la política que define el backend. */
function applyPolicy(policy) {
  const { min, max, default: defaultLength } = policy.length;
  ui.lengthInput.min = String(min);
  ui.lengthInput.max = String(max);
  ui.lengthInput.value = String(defaultLength);
  syncLengthValue();
  ui.checkInput.maxLength = policy.max_password_input_length;
}

async function connectToApi() {
  try {
    await getHealth();
    setApiStatus("online", "Servidor conectado");
  } catch {
    setApiStatus("offline", "Sin conexión con el servidor");
    return;
  }
  try {
    applyPolicy(await getPasswordOptions());
  } catch (error) {
    console.warn("No se pudo cargar la política; se usan los valores por defecto.", error);
  }
}

function init() {
  ui.lengthInput.addEventListener("input", syncLengthValue);
  ui.generatorForm.addEventListener("submit", handleGenerate);
  ui.copyButton.addEventListener("click", handleCopy);
  ui.checkerForm.addEventListener("submit", handleCheck);
  ui.toggleVisibility.addEventListener("click", handleToggleVisibility);
  syncLengthValue();
  connectToApi();
}

init();
