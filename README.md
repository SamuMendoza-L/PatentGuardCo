# Patentes en disputa API

API FastAPI para evaluar la integridad de evidencia técnica asociada a disputas de autoría de patentes.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configura `GEMINI_API_KEY` en `.env` y ejecuta la aplicación:

```bash
uvicorn app.main:app --reload
```

La documentación interactiva estará disponible en `/docs`. Ejecuta las pruebas con `pytest`.
