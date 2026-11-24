"""Pruebas unitarias para el servicio de decisión JEV."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.jev_service import (
    evaluar_decision_jev,
    _generar_decision_deterministica,
    decision_cache,
)


@pytest.fixture(autouse=True)
def limpiar_cache_jev():
    decision_cache.clear()


@pytest.mark.asyncio
async def test_decision_jev_disputa_directa():
    """Con reclamantes e inconsistencias, el clasificador determina DISPUTA_AUTORIA_DIRECTA."""
    datos = {
        "patentes_consultadas": [{"numero_solicitud": "NC2026/000123", "titulo": "Test"}]
    }
    inconsistencias = ["[NC2026/000123] Advertencia: Campo recomendado ausente: 'inventor'"]
    reclamantes = ["Samuel Mendoza", "David Ospina"]

    resultado = await evaluar_decision_jev(
        datos_patente=datos,
        inconsistencias_tecnicas=inconsistencias,
        inventores_reclamantes=reclamantes
    )

    assert resultado["tipo_conflicto"] == "DISPUTA_AUTORIA_DIRECTA"
    assert resultado["score_severidad"] >= 4.0
    assert resultado["accion_recomendada"] == "REVISION_PRIORITARIA"
    assert resultado["requiere_peritaje"] is True


@pytest.mark.asyncio
async def test_decision_jev_anomalia_temporal():
    """Con inconsistencias de fechas, determina INCONSISTENCIA_TEMPORAL."""
    datos = {
        "patentes_consultadas": [{"numero_solicitud": "NC2026/000123", "titulo": "Test"}]
    }
    inconsistencias = ["Inconsistencia temporal: La fecha de publicación es anterior a la fecha de radicación"]

    resultado = await evaluar_decision_jev(
        datos_patente=datos,
        inconsistencias_tecnicas=inconsistencias,
        inventores_reclamantes=[]
    )

    assert resultado["tipo_conflicto"] == "INCONSISTENCIA_TEMPORAL"
    assert resultado["requiere_peritaje"] is True


@pytest.mark.asyncio
async def test_decision_jev_omision_formal():
    """Con campos ausentes sin reclamantes, determina OMISION_FORMAL."""
    datos = {
        "patentes_consultadas": [{"numero_solicitud": "NC2026/000123", "titulo": "Test"}]
    }
    inconsistencias = ["Campo recomendado ausente: 'solicitante'"]

    resultado = await evaluar_decision_jev(
        datos_patente=datos,
        inconsistencias_tecnicas=inconsistencias,
        inventores_reclamantes=[]
    )

    assert resultado["tipo_conflicto"] == "OMISION_FORMAL"
    assert resultado["accion_recomendada"] == "AUDITORIA_DOCUMENTAL"
    assert resultado["requiere_peritaje"] is False


@pytest.mark.asyncio
async def test_decision_jev_mock_ollama_exitoso():
    """Verifica el parseo de salida JSON Schema cuando Ollama responde 200 OK."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {
            "content": '{"tipo_conflicto": "DISPUTA_AUTORIA_DIRECTA", "confianza_tipo": 0.95, "score_severidad": 4.8, "accion_recomendada": "REVISION_PRIORITARIA", "requiere_peritaje": true, "justificacion_breve": "Clara omisión de inventores."}'
        }
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    datos = {"patentes_consultadas": [{"numero_solicitud": "NC2026/000999"}]}
    resultado = await evaluar_decision_jev(
        datos_patente=datos,
        inconsistencias_tecnicas=["Error"],
        inventores_reclamantes=["Reclamante 1"],
        client=mock_client
    )

    assert resultado["tipo_conflicto"] == "DISPUTA_AUTORIA_DIRECTA"
    assert resultado["confianza_tipo"] == 0.95
    assert resultado["score_severidad"] == 4.8
    assert "JEV_LOCAL_OLLAMA" in resultado["proveedor"]
