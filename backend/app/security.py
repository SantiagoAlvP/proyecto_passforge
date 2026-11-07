"""Cabeceras HTTP de seguridad que se añaden a todas las respuestas."""

from __future__ import annotations

from flask import Flask, Response

# Al ser una API que solo devuelve JSON, la política puede ser muy estricta.
_SECURITY_HEADERS = {
    # Evita que el navegador "adivine" el tipo de contenido (MIME sniffing).
    "X-Content-Type-Options": "nosniff",
    # La API no debe mostrarse dentro de iframes (clickjacking).
    "X-Frame-Options": "DENY",
    # No se carga ningún recurso desde una respuesta de la API.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    # No enviar la URL de origen a terceros.
    "Referrer-Policy": "no-referrer",
    # Las respuestas contienen contraseñas: no deben quedar en ninguna caché.
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
}


def register_security_headers(app: Flask) -> None:
    """Registra un ``after_request`` que añade las cabeceras de seguridad."""

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        if app.config["HSTS_ENABLED"]:
            # Solo tiene efecto cuando la app se sirve por HTTPS.
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
