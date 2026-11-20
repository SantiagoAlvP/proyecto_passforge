# PassForge · Frontend

Interfaz web en **HTML, CSS y JavaScript puro** (sin frameworks ni paso de
compilación). Se comunica con el backend Flask mediante su API REST.

## Puesta en marcha

Necesita el backend en ejecución en `http://127.0.0.1:8000` (ver `../backend`).

```bash
cd frontend
python3 -m http.server 5500 --bind 127.0.0.1
```

Abre <http://127.0.0.1:5500>.

> Se necesita un servidor HTTP: los módulos de JavaScript (`type="module"`)
> no funcionan abriendo el archivo directamente (`file://`).

## Con Docker

La imagen usa **nginx sin privilegios** (puerto 8080). Al arrancar, el script
`docker/40-passforge-config.sh` genera `js/config.js` con el valor de la
variable `API_BASE_URL` (por defecto `/api/v1`), así la misma imagen funciona
en cualquier ambiente:

```bash
docker build -t passforge-frontend .
docker run -p 8080:8080 -e API_BASE_URL=http://localhost:8000/api/v1 passforge-frontend
```

Para levantar la app completa usa `docker compose up --build` desde la raíz.

## Estructura

```
frontend/
├── index.html        # estructura de la página
├── css/styles.css    # estilos (tema claro/oscuro automático)
├── js/
│   ├── config.js     # URL del backend (único lugar a cambiar)
│   ├── api.js        # cliente HTTP: todas las llamadas al API
│   └── app.js        # lógica de la interfaz
├── assets/favicon.svg
├── docker/
│   ├── nginx.conf              # servidor y health check /health
│   ├── security-headers.conf   # cabeceras de seguridad
│   └── 40-passforge-config.sh  # genera config.js al arrancar
└── Dockerfile
```

## Buenas prácticas aplicadas

- **Separación de responsabilidades**: configuración, acceso al API e interfaz
  en módulos distintos.
- **Sin XSS**: los datos se insertan con `textContent`, nunca con `innerHTML`.
- **Content Security Policy** estricta: sin scripts ni estilos *inline* y sin
  recursos de terceros; solo puede conectarse con el backend.
- **Sin persistencia de secretos**: la contraseña solo vive en memoria.
- Peticiones con **tiempo de espera**, `credentials: "omit"` y `cache: "no-store"`.
- **Accesible**: etiquetas en todos los campos, regiones `aria-live`, foco
  visible, respeta `prefers-reduced-motion` y funciona en móvil.
- Atributos `data-testid` estables para las pruebas de aceptación.
