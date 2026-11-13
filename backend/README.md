# PassForge · Backend (Flask)

API REST que genera contraseñas aleatorias seguras y evalúa la fortaleza de
una contraseña. No guarda nada: no tiene base de datos ni registra contraseñas.

## Requisitos

- Python 3.10 o superior (recomendado 3.13)

> **macOS:** el `python3` que trae el sistema (`/usr/bin/python3`) es 3.9 y
> **no sirve**. Instala uno reciente con `brew install python@3.13` y crea el
> entorno virtual con `python3.13 -m venv .venv`.

## Puesta en marcha

```bash
cd backend
python3.13 -m venv .venv          # Python 3.10+ (en macOS no uses el python3 del sistema)
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # ajusta los valores si hace falta
python wsgi.py
```

La API queda en `http://127.0.0.1:8000/api/v1`.

> En macOS se usa el puerto **8000** porque el 5000 lo ocupa *AirPlay Receiver*.

## Endpoints

| Método | Ruta                           | Descripción                                   |
|--------|--------------------------------|-----------------------------------------------|
| GET    | `/api/v1/health`               | Estado del servicio (`{"status": "ok"}`).     |
| GET    | `/api/v1/passwords/options`    | Política: longitudes y conjuntos de caracteres.|
| POST   | `/api/v1/passwords/generate`   | Genera una contraseña aleatoria.              |
| POST   | `/api/v1/passwords/strength`   | Evalúa la fortaleza de una contraseña.        |

### `POST /api/v1/passwords/generate`

Todos los campos son opcionales:

| Campo               | Tipo    | Por defecto | Regla        |
|---------------------|---------|-------------|--------------|
| `length`            | entero  | 16          | 8 a 128      |
| `include_lowercase` | booleano| `true`      |              |
| `include_uppercase` | booleano| `true`      |              |
| `include_digits`    | booleano| `true`      |              |
| `include_symbols`   | booleano| `true`      |              |
| `exclude_ambiguous` | booleano| `false`     | quita `Il1O0o` |

Al menos uno de los `include_*` debe ser `true`.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/passwords/generate \
  -H "Content-Type: application/json" \
  -d '{"length": 20, "include_symbols": false}'
```

```json
{
  "password": "x8RkT2mQv9LpW4nZs7Ya",
  "length": 20,
  "strength": { "score": 3, "label": "fuerte", "entropy_bits": 119.08, "feedback": [] }
}
```

### `POST /api/v1/passwords/strength`

```bash
curl -X POST http://127.0.0.1:8000/api/v1/passwords/strength \
  -H "Content-Type: application/json" \
  -d '{"password": "abc123"}'
```

```json
{
  "score": 0,
  "label": "muy débil",
  "entropy_bits": 31.02,
  "feedback": ["Es una contraseña muy común y fácil de adivinar."]
}
```

`score` va de 0 a 4: `muy débil`, `débil`, `aceptable`, `fuerte`, `muy fuerte`.

### Formato de errores

Todos los errores comparten el mismo formato:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Datos de entrada inválidos.",
    "details": { "length": "Debe estar entre 8 y 128." }
  }
}
```

## Estructura

```
backend/
├── app/
│   ├── __init__.py              # create_app(): application factory
│   ├── config.py                # configuración por entorno (variables de entorno)
│   ├── extensions.py            # CORS y rate limiter
│   ├── security.py              # cabeceras HTTP de seguridad
│   ├── errors.py                # errores en JSON uniforme
│   ├── validators.py            # validación de entrada
│   ├── api/
│   │   └── routes.py            # endpoints /api/v1 (capa HTTP delgada)
│   └── services/
│       └── password_service.py  # lógica de negocio pura (sin Flask)
├── tests/
│   ├── conftest.py              # fixtures compartidas (app, client, make_app)
│   ├── unit/                    # pruebas unitarias
│   ├── module/                  # pruebas modulares
│   └── integration/             # pruebas de integración
├── wsgi.py                      # punto de entrada
├── pyproject.toml               # configuración de pytest y coverage
├── requirements.txt             # dependencias de ejecución
├── requirements-dev.txt         # + dependencias de pruebas
└── .env.example
```

La lógica está separada en capas: **rutas** (HTTP) → **validadores** →
**servicios** (lógica pura). Así cada pieza se puede probar por separado.

## Pruebas

Las pruebas están organizadas en tres niveles. Todas siguen la estrategia
**AAA** (*Arrange, Act, Assert*).

| Nivel | Carpeta | Qué prueba | Cómo |
|---|---|---|---|
| **Unitarias** | `tests/unit/` | Una función o clase | Aislada; el azar o las dependencias se reemplazan por dobles de prueba (`monkeypatch`) |
| **Modulares** | `tests/module/` | Un módulo completo (servicio, validación, config, errores, seguridad) | Por su interfaz pública, con sus partes reales, sin el resto de la app (o en una app Flask vacía) |
| **Integración** | `tests/integration/` | La app completa | `create_app()` sin dobles: CORS, rate limit, validación, servicio, errores y cabeceras juntos; incluye un servidor HTTP real |

```bash
pip install -r requirements-dev.txt

pytest                      # todas las pruebas
pytest -v                   # con el nombre de cada prueba
pytest -m unit              # solo un nivel: unit | module | integration
pytest tests/integration    # o por carpeta
```

### Cobertura

```bash
pytest --cov --cov-report=term-missing   # reporte en consola
pytest --cov --cov-report=html           # reporte visual en htmlcov/index.html
```

Se mide la cobertura de **líneas y ramas** (`branch = true` en `pyproject.toml`).

## Medidas de seguridad aplicadas

- **Aleatoriedad criptográfica**: se usa `secrets` (nunca `random`).
- **Validación estricta** de tipo, rango y campos permitidos (lista blanca).
- **Límite de tamaño** del cuerpo de la petición (2 KB) y de la contraseña a evaluar.
- **Rate limiting** por IP (60/min general, 30/min en los endpoints POST).
- **CORS restringido** a los orígenes configurados; en producción `*` está prohibido.
- **Cabeceras de seguridad**: `nosniff`, `X-Frame-Options`, CSP, `no-referrer`,
  `Cache-Control: no-store` (las contraseñas no se cachean) y HSTS en producción.
- **Errores sin filtrar detalles internos**: el stack trace va a los logs, no al cliente.
- **Las contraseñas nunca se registran** en logs ni se almacenan.
- **Seguro por defecto**: si no se define `APP_ENV`, arranca en `production`
  (sin debug) y exige `CORS_ORIGINS`.
- **Configuración por variables de entorno**; `.env` está excluido de Git.
- **Dependencias con versión fijada** para builds reproducibles.
- El modo debug solo escucha en `127.0.0.1`.
