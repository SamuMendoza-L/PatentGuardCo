import os
import json
import pytest
from unittest.mock import MagicMock, patch
from google.genai.errors import APIError

from app.gemini_service import (
    evaluar_disputa_con_gemini,
    GeminiServiceError
)


@pytest.fixture
def mock_gemini_client():
    """Fixture que proporciona un mock configurado del cliente de google-genai."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "resumen": "Análisis de trazabilidad para la patente solicitada.",
        "hechos_verificados": ["Solicitud radicado con el ID NC2026/000123."],
        "inconsistencias": ["Ausencia del campo recomendado 'inventor'."],
        "informacion_faltante": ["Bitácoras de commits y firmas de desarrollo."],
        "analisis_etico": {
            "riesgo_etico": "Riesgo de omisión del derecho moral de autoría.",
            "autoria_vs_lucro": "La autoría es un derecho moral inalienable primario; el lucro es patrimonial y derivado.",
            "descargo_legal": "Este análisis no constituye prueba ni dictamen judicial vinculante."
        },
        "recomendaciones": ["Verificar actas de cesión de derechos con el titular."]
    })
    client.models.generate_content.return_value = mock_response
    return client


def test_evaluar_disputa_exitoso(mock_gemini_client):
    """Verifica que el servicio procese la respuesta estructurada correctamente."""
    datos = {"numero_solicitud": "NC2026/000123", "titulo": "Sistema IA"}
    inconsistencias = ["Falta inventor"]
    reclamantes = ["Samuel Mendoza", "Andrés Felipe"]

    resultado = evaluar_disputa_con_gemini(
        datos_patente=datos,
        inconsistencias_tecnicas=inconsistencias,
        inventores_reclamantes=reclamantes,
        client=mock_gemini_client
    )

    assert resultado["resumen"] == "Análisis de trazabilidad para la patente solicitada."
    assert "hechos_verificados" in resultado
    assert "autoria_vs_lucro" in resultado["analisis_etico"]
    assert mock_gemini_client.models.generate_content.called


def test_error_falta_api_key():
    """Verifica la excepción cuando no está presente la variable GEMINI_API_KEY."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(GeminiServiceError) as exc_info:
            evaluar_disputa_con_gemini({}, [])
        assert "GEMINI_API_KEY" in str(exc_info.value)


def test_manejo_error_limite_cuota(mock_gemini_client):
    """Verifica la captura de errores HTTP 429 de tasa de límite (Rate Limit)."""
    error = APIError(
        code=429,
        response_json={
            "error": {
                "code": 429,
                "message": "RESOURCE_EXHAUSTED",
                "status": "RESOURCE_EXHAUSTED",
            }
        },
        response=None,
    )
    mock_gemini_client.models.generate_content.side_effect = error

    with pytest.raises(GeminiServiceError) as exc_info:
        evaluar_disputa_con_gemini({}, [], client=mock_gemini_client)

    assert "Límite de cuota excedido" in str(exc_info.value)


def test_manejo_respuesta_json_invalida(mock_gemini_client):
    """Verifica la captura de respuestas que no cumplen la estructura JSON."""
    mock_response = MagicMock()
    mock_response.text = "Respuesta en texto plano no JSON"
    mock_gemini_client.models.generate_content.return_value = mock_response

    with pytest.raises(GeminiServiceError) as exc_info:
        evaluar_disputa_con_gemini({}, [], client=mock_gemini_client)

    assert "Error al parsear JSON" in str(exc_info.value)
