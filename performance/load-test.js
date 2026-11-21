// Pruebas de rendimiento de PassForge con k6 (modificación 2 del proyecto final).
//
// Se ejecutan contra un ambiente desplegado (Staging) ANTES de pasar a
// Producción. Si se rompe algún umbral (thresholds), k6 termina con código de
// salida distinto de 0 y el pipeline se detiene: la versión no llega a Producción.
//
// Variables de entorno:
//   BASE_URL      URL del ambiente, sin "/" al final (ALB: /api/* va al backend)
//                 ej: http://passforge-staging-alb-123.us-east-1.elb.amazonaws.com
//   API_PREFIX    prefijo de la API (por defecto /api/v1)
//   RATE_LIMIT_BURST  peticiones de la ráfaga del escenario rate_limit (100)
//   TEST_PROFILE  "gate" (por defecto): prueba corta que decide si se promueve.
//                 "stress": carga sostenida para demostrar el autoescalado.
//
// Escenarios del perfil "gate" (~2 minutos):
//   1. carga       Muchos usuarios concurrentes sobre /health (exento del rate
//                  limit): mide latencia y errores del ALB + backend bajo carga.
//   2. funcional   Generar y evaluar contraseñas a un ritmo por debajo del rate
//                  limit (30/min por IP): valida respuestas correctas y latencia.
//   3. rate_limit  Ráfaga final sobre /generate: comprueba que la protección
//                  contra abuso responde 429 (control de seguridad activo).

import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const API = `${BASE_URL}${__ENV.API_PREFIX || "/api/v1"}`;
const PROFILE = __ENV.TEST_PROFILE || "gate";
const BURST = parseInt(__ENV.RATE_LIMIT_BURST || "100", 10);

const JSON_HEADERS = { headers: { "Content-Type": "application/json" } };
const rateLimited = new Counter("rate_limited_responses");

const gateScenarios = {
  carga: {
    executor: "ramping-vus",
    exec: "cargaHealth",
    startVUs: 0,
    stages: [
      { duration: "20s", target: 20 },
      { duration: "40s", target: 20 },
      { duration: "10s", target: 0 },
    ],
    tags: { escenario: "carga" },
  },
  funcional: {
    executor: "constant-arrival-rate",
    exec: "funcional",
    rate: 20, // iteraciones por minuto: por debajo del límite de 30/min por IP
    timeUnit: "1m",
    duration: "70s",
    preAllocatedVUs: 2,
    tags: { escenario: "funcional" },
  },
  rate_limit: {
    executor: "per-vu-iterations",
    exec: "rafagaRateLimit",
    vus: 1,
    iterations: 1,
    startTime: "75s", // después de los otros escenarios
    tags: { escenario: "rate_limit" },
  },
};

const stressScenarios = {
  estres: {
    executor: "ramping-vus",
    exec: "cargaHealth",
    startVUs: 0,
    stages: [
      { duration: "1m", target: 50 },
      { duration: "4m", target: 100 },
      { duration: "1m", target: 0 },
    ],
    tags: { escenario: "estres" },
  },
};

export const options = {
  scenarios: PROFILE === "stress" ? stressScenarios : gateScenarios,
  thresholds:
    PROFILE === "stress"
      ? {
          "http_req_failed{escenario:estres}": ["rate<0.05"],
        }
      : {
          // Latencia: el 95 % de las peticiones por debajo del umbral.
          "http_req_duration{escenario:carga}": ["p(95)<500"],
          "http_req_duration{escenario:funcional}": ["p(95)<800"],
          // Errores: menos del 1 % (respuestas 5xx, timeouts, 4xx inesperados).
          "http_req_failed{escenario:carga}": ["rate<0.01"],
          "http_req_failed{escenario:funcional}": ["rate<0.01"],
          // Todas las validaciones funcionales deben pasar.
          "checks{escenario:funcional}": ["rate>0.99"],
          // El rate limit debe estar activo: al menos una respuesta 429.
          rate_limited_responses: ["count>0"],
        },
  summaryTrendStats: ["avg", "min", "med", "p(90)", "p(95)", "max"],
};

export function cargaHealth() {
  const res = http.get(`${API}/health`, { tags: { endpoint: "health" } });
  check(res, {
    "health responde 200": (r) => r.status === 200,
    "health status ok": (r) => r.json("status") === "ok",
  });
  sleep(0.2);
}

export function funcional() {
  const gen = http.post(
    `${API}/passwords/generate`,
    JSON.stringify({ length: 24, include_symbols: true }),
    { ...JSON_HEADERS, tags: { endpoint: "generate" } },
  );
  check(gen, {
    "generate responde 200": (r) => r.status === 200,
    "generate respeta la longitud": (r) =>
      r.status === 200 && r.json("password").length === 24,
    "generate incluye fortaleza": (r) =>
      r.status === 200 && typeof r.json("strength.score") === "number",
  });

  const pwd = gen.status === 200 ? gen.json("password") : "Tr0ub4dor&3xyz!";
  const str = http.post(
    `${API}/passwords/strength`,
    JSON.stringify({ password: pwd }),
    { ...JSON_HEADERS, tags: { endpoint: "strength" } },
  );
  check(str, {
    "strength responde 200": (r) => r.status === 200,
    "strength devuelve label": (r) =>
      r.status === 200 && typeof r.json("label") === "string",
  });
}

export function rafagaRateLimit() {
  // Ráfaga de peticiones seguidas: el límite es 30/min por IP, así que deben
  // llegar respuestas 429. Aquí 429 es un resultado ESPERADO, no un error.
  // Ojo: con RATELIMIT_STORAGE_URI=memory:// cada worker de Gunicorn (2 por
  // tarea) y cada tarea de ECS lleva su propio contador, así que el límite real
  // es 30 x workers x tareas. Por eso la ráfaga es de 100 por defecto.
  const params = {
    ...JSON_HEADERS,
    tags: { endpoint: "generate" },
    responseCallback: http.expectedStatuses(200, 429),
  };
  for (let i = 0; i < BURST; i++) {
    const res = http.post(`${API}/passwords/generate`, JSON.stringify({}), params);
    if (res.status === 429) {
      rateLimited.add(1);
    }
  }
}
