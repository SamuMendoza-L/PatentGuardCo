"""Prueba de concurrencia en memoria para el endpoint de análisis."""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app


PAYLOAD = {
    "numeros_solicitud": ["NC2026/000123"],
    "descripcion_conflicto": "Descripción de una disputa de autoría suficientemente detallada.",
}
PATENTE_SIMULADA = {
    "numero_solicitud": "NC2026/000123",
    "titulo": "Patente de prueba concurrente",
    "solicitante": "Entidad de prueba",
    "inventor": "Persona de prueba",
}
ANALISIS_SIMULADO = {
    "resumen": "Análisis simulado.",
    "hechos_verificados": [],
    "inconsistencias": [],
    "informacion_faltante": [],
    "analisis_etico": {},
    "recomendaciones": [],
}


@pytest.mark.asyncio
async def test_analizar_conflicto_soporta_25_peticiones_concurrentes():
    """Verifica aislamiento de solicitudes y métrica interna con dependencias simuladas."""
    with (
        patch(
            "app.main.consultar_patente_por_numero_solicitud",
            new=AsyncMock(return_value=PATENTE_SIMULADA),
        ) as mock_datos_abiertos,
        patch("app.main.evaluar_disputa_con_gemini", return_value=ANALISIS_SIMULADO) as mock_gemini,
    ):
        transporte = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://testserver") as cliente:
            respuestas = await asyncio.gather(
                *(cliente.post("/analizar-conflicto", json=PAYLOAD) for _ in range(25))
            )

    assert all(respuesta.status_code == 200 for respuesta in respuestas)
    cuerpos = [respuesta.json() for respuesta in respuestas]
    assert all(cuerpo["status"] == "success" for cuerpo in cuerpos)
    assert all(cuerpo["resumen_procesamiento"]["registros_encontrados"] == 1 for cuerpo in cuerpos)
    assert sum(cuerpo["resumen_procesamiento"]["tiempo_procesamiento_ms"] for cuerpo in cuerpos) / len(cuerpos) < 150
    assert mock_datos_abiertos.await_count == 25
    assert mock_gemini.call_count == 25
