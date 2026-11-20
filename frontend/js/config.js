/**
 * Configuración del frontend.
 *
 * Es el ÚNICO lugar donde se define la dirección del backend.
 * - Desarrollo local (python -m http.server 5500): el backend está en :8000.
 * - Docker / AWS: un balanceador (ALB o el gateway de docker-compose) sirve
 *   frontend y backend en el mismo origen y enruta /api/* al backend, así que
 *   basta con una ruta relativa.
 */
const API_PORT = 8000;
const LOCAL_DEV_PORT = "5500";

export const API_BASE_URL =
  window.location.port === LOCAL_DEV_PORT
    ? `${window.location.protocol}//${window.location.hostname}:${API_PORT}/api/v1`
    : "/api/v1";

/** Tiempo máximo de espera de una petición, en milisegundos. */
export const REQUEST_TIMEOUT_MS = 8000;