# Imagen del backend (API Flask) de PassForge
FROM python:3.13-slim

# Sin archivos .pyc y logs sin buffer (se ven al instante en CloudWatch)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

WORKDIR /app

# Primero solo las dependencias para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario sin privilegios (no correr como root)
RUN useradd --create-home --uid 10001 appuser

# Solo el código necesario para ejecutar (sin pruebas)
COPY app/ ./app/
COPY wsgi.py .

EXPOSE 8000
USER appuser

# Health check del contenedor (python-slim no trae curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

# 2 workers: suficiente para una tarea Fargate de 0.25 vCPU
CMD ["gunicorn", "--workers=2", "--bind=0.0.0.0:8000", "--access-logfile=-", "wsgi:app"]