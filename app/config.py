"""Configuración de la aplicación obtenida desde variables de entorno."""

import os

from dotenv import load_dotenv


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DATOS_ABIERTOS_RESOURCE_URL = os.getenv("DATOS_ABIERTOS_RESOURCE_URL")
