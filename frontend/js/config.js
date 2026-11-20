/**
 * Configuración del frontend para DESARROLLO LOCAL.
 *
 * Es el ÚNICO lugar donde se define la dirección del backend. Se usa el mismo
 * host desde el que se abrió la página (localhost o 127.0.0.1) para que el
 * origen coincida con los permitidos en CORS.
 *
 * En el contenedor Docker este archivo se reemplaza al arrancar con el valor
 * de la variable de entorno API_BASE_URL (ver docker/40-passforge-config.sh).
 */
const API_PORT = 8000;

export const API_BASE_URL =
  `${globalThis.location.protocol}//${globalThis.location.hostname}:${API_PORT}/api/v1`;

/** Tiempo máximo de espera de una petición, en milisegundos. */
export const REQUEST_TIMEOUT_MS = 8000;
