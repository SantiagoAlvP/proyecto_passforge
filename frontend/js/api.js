/**
 * Cliente del API de PassForge.
 *
 * Centraliza todas las llamadas HTTP: URL base, cabeceras, tiempo de espera
 * y conversión de errores. El resto de la app nunca usa `fetch` directamente.
 */
import { API_BASE_URL, REQUEST_TIMEOUT_MS } from "./config.js";

/** Error con un mensaje listo para mostrar al usuario. */
export class ApiError extends Error {
  constructor(message, { status = 0, details = {} } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function request(path, { method = "GET", body } = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
      credentials: "omit", // la API no usa cookies
      cache: "no-store", // las respuestas contienen contraseñas
      referrerPolicy: "no-referrer",
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError("El servidor tardó demasiado en responder. Inténtalo de nuevo.");
    }
    throw new ApiError(
      "No se pudo conectar con el servidor. Comprueba que el backend esté en ejecución.",
    );
  } finally {
    clearTimeout(timeoutId);
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const error = data?.error ?? {};
    throw new ApiError(
      error.message ?? `El servidor respondió con un error (HTTP ${response.status}).`,
      { status: response.status, details: error.details ?? {} },
    );
  }
  return data;
}

/** GET /health */
export function getHealth() {
  return request("/health");
}

/** GET /passwords/options */
export function getPasswordOptions() {
  return request("/passwords/options");
}

/**
 * POST /passwords/generate
 * @param {{length:number, include_lowercase:boolean, include_uppercase:boolean,
 *          include_digits:boolean, include_symbols:boolean,
 *          exclude_ambiguous:boolean}} options
 */
export function generatePassword(options) {
  return request("/passwords/generate", { method: "POST", body: options });
}

/** POST /passwords/strength */
export function checkPasswordStrength(password) {
  return request("/passwords/strength", { method: "POST", body: { password } });
}
