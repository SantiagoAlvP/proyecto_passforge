# Imagen del frontend de PassForge: archivos estáticos servidos con nginx.
# Variante "unprivileged": nginx corre sin root y escucha en el puerto 8080.
FROM nginxinc/nginx-unprivileged:1.30-alpine

# Solo durante la construcción se usa root (para copiar y ajustar permisos);
# al final se vuelve al usuario sin privilegios.
USER root

# Configuración de nginx y script que genera js/config.js al arrancar.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY docker/40-passforge-config.sh /docker-entrypoint.d/40-passforge-config.sh

# Archivos estáticos.
COPY index.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/
COPY assets/ /usr/share/nginx/html/assets/

# Permisos explícitos (no dependen de los del equipo donde se construye):
# todo es de root y nginx solo puede leerlo, excepto config.js, que el script
# reescribe al iniciar el contenedor.
RUN chmod -R a+rX /usr/share/nginx/html /etc/nginx/conf.d /etc/nginx/snippets \
    && chmod 0755 /docker-entrypoint.d/40-passforge-config.sh \
    && chown 101:101 /usr/share/nginx/html/js/config.js

# URL del backend que usará el navegador. Se cambia al ejecutar el contenedor
# (docker run -e / docker compose / ECS) sin volver a construir la imagen.
ENV API_BASE_URL=/api/v1

# Usuario sin privilegios (uid 101 = nginx).
USER 101

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1
