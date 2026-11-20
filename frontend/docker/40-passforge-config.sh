#!/bin/sh
# Genera js/config.js a partir de la variable de entorno API_BASE_URL.
#
# Así la MISMA imagen sirve en cualquier ambiente (local, CI, staging,
# producción): solo cambia la variable, no se vuelve a construir la imagen.
# La imagen oficial de nginx ejecuta los scripts de /docker-entrypoint.d/
# antes de arrancar el servidor.
set -eu

CONFIG_FILE=/usr/share/nginx/html/js/config.js
API_BASE_URL="${API_BASE_URL:-/api/v1}"

# Seguridad: el valor se escribe dentro de un archivo JavaScript, así que solo
# se aceptan caracteres válidos en una URL (evita inyectar código).
case "$API_BASE_URL" in
  *[!A-Za-z0-9:/._-]*)
    echo "ERROR: API_BASE_URL contiene caracteres no permitidos: $API_BASE_URL" >&2
    exit 1
    ;;
esac

cat > "$CONFIG_FILE" <<EOF
// Archivo generado al iniciar el contenedor (docker/40-passforge-config.sh).
export const API_BASE_URL = "${API_BASE_URL}";
export const REQUEST_TIMEOUT_MS = 8000;
EOF

echo "PassForge: API_BASE_URL=${API_BASE_URL}"
