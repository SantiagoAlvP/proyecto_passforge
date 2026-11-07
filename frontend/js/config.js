/**
 * Configuración del frontend.
 *
 * Es el ÚNICO lugar donde se define la dirección del backend. Se usa el mismo
 * host desde el que se abrió la página (localhost o 127.0.0.1) para que el
 * origen coincida con los permitidos en CORS. Al dockerizar, este archivo se
 * podrá generar a partir de variables de entorno.
 */
const API_PORT = 8000;

export const API_BASE_URL =
  `${window.location.protocol}//${window.location.hostname}:${API_PORT}/api/v1`;

/** Tiempo máximo de espera de una petición, en milisegundos. */
export const REQUEST_TIMEOUT_MS = 8000;
