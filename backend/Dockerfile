# Imagen del backend de PassForge (API Flask servida con Gunicorn).
# Versión fija de Python: la misma que usan el pipeline y el desarrollo local.
FROM python:3.13-slim

# - Sin archivos .pyc y con logs sin búfer (se ven al instante en "docker logs").
# - APP_ENV=production: sin debug y exige CORS_ORIGINS (seguro por defecto).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production

WORKDIR /app

# Primero solo las dependencias: esta capa se reutiliza de la caché mientras
# requirements.txt no cambie, aunque cambie el código.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Luego el código. Solo lo necesario para ejecutar: sin pruebas ni linters.
COPY app/ ./app/
COPY wsgi.py .

# - Permisos explícitos (no dependen de los del equipo donde se construye):
#   el código es de root y los demás usuarios solo pueden leerlo.
# - Usuario sin privilegios: si alguien comprometiera la app, no sería root.
RUN chmod -R a+rX /app \
    && useradd --no-create-home --uid 10001 --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 8000

# Docker marca el contenedor como "healthy" cuando /api/v1/health responde.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"]

# Gunicorn: servidor WSGI de producción. Escucha en 0.0.0.0 porque dentro del
# contenedor debe aceptar conexiones que llegan desde fuera de él.
# --no-control-socket: Gunicorn 26 crea por defecto un socket de administración
# en $HOME, que no existe para el usuario sin privilegios; no se necesita.
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=2", "--no-control-socket", "--access-logfile=-", "wsgi:app"]
