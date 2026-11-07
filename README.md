# PassForge

Generador de contraseñas aleatorias seguras con comprobador de fortaleza.

Proyecto del curso **Integración y Entrega Continua de Software**. La app es
deliberadamente sencilla: el objetivo del curso es construir a su alrededor
pruebas unitarias, cobertura, pruebas de aceptación y, más adelante, todo el
ciclo DevOps (Docker, CI/CD).

## Arquitectura

No es un monolito: frontend y backend son aplicaciones independientes que se
comunican por una API REST en JSON. Cada una irá en su propio contenedor.

```
┌──────────────────────────┐   HTTP/JSON (CORS)   ┌──────────────────────────┐
│  frontend/               │ ───────────────────▶ │  backend/                │
│  HTML + CSS + JS         │                      │  Python + Flask          │
│  http://127.0.0.1:5500   │ ◀─────────────────── │  http://127.0.0.1:8000   │
└──────────────────────────┘                      └──────────────────────────┘
```

## API (resumen)

| Método | Ruta                          | Descripción                          |
|--------|-------------------------------|--------------------------------------|
| GET    | `/api/v1/health`              | Estado del servicio                  |
| GET    | `/api/v1/passwords/options`   | Política y opciones admitidas        |
| POST   | `/api/v1/passwords/generate`  | Genera una contraseña aleatoria      |
| POST   | `/api/v1/passwords/strength`  | Evalúa la fortaleza de una contraseña|

Detalle completo en [`backend/README.md`](backend/README.md).

## Ejecutar en local

Terminal 1 — backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python wsgi.py
```

Terminal 2 — frontend:

```bash
cd frontend
python3 -m http.server 5500 --bind 127.0.0.1
```

Abre <http://127.0.0.1:5500>.

## Estructura

```
passforge/
├── backend/     # API REST en Flask
├── frontend/    # interfaz web estática
├── .editorconfig
├── .gitignore
└── README.md
```
