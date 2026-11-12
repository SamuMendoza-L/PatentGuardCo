"""Pruebas no funcionales de seguridad sin dependencias de red externas."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.client_datos_abiertos import consultar_patente_por_numero_solicitud
from app.gemini_service import GeminiServiceError
from app.main import app


client = TestClient(app)


def _payload() -> dict:
    return {
        "numeros_solicitud": ["NC2026/000123"],
        "descripcion_conflicto": "Descripción de una disputa de autoría suficientemente detallada.",
    }


@pytest.mark.asyncio
async def test_sanitiza_intento_de_inyeccion_soql():
    """La consulta SoQL conserva el valor como literal y elimina comillas peligrosas."""
    respuesta = MagicMock()
    respuesta.raise_for_status.return_value = None
    respuesta.json.return_value = []

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=respuesta)) as mock_get:
        resultado = await consultar_patente_por_numero_solicitud("99020335' OR '1'='1\n")

    assert resultado is None
    assert mock_get.await_args.kwargs["params"]["$where"] == "solicitud = '99020335 OR 1=1'"


@patch("app.main.consultar_patente_por_numero_solicitud", new_callable=AsyncMock)
@patch("app.main.evaluar_disputa_con_gemini")
def test_respuesta_no_filtra_secretos_ni_rutas_internas(mock_gemini, mock_datos_abiertos):
    """Los detalles de errores externos no se devuelven al consumidor de la API."""
    secreto = "clave-super-secreta-de-prueba"
    ruta_interna = "/private/var/folders/proyecto/.env"
    mock_datos_abiertos.return_value = {
        "numero_solicitud": "NC2026/000123",
        "titulo": "Patente de prueba",
        "solicitante": "Entidad de prueba",
        "inventor": "Persona de prueba",
    }
    mock_gemini.side_effect = GeminiServiceError(f"Fallo con {secreto} en {ruta_interna}")

    response = client.post("/analizar-conflicto", json=_payload())

    assert response.status_code == 200
    assert secreto not in response.text
    assert ruta_interna not in response.text
    assert "no disponible temporalmente" in response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"numeros_solicitud": {"corrupto": "NC2026/000123"}, "descripcion_conflicto": "Descripción válida para la auditoría."},
        {"numeros_solicitud": ["NC2026/000123"], "descripcion_conflicto": "x" * 5001},
        {"numeros_solicitud": ["x" * 101], "descripcion_conflicto": "Descripción válida para la auditoría."},
    ],
)
def test_rechaza_payloads_corruptos_o_excesivamente_largos(payload):
    """El contrato rechaza tipos no válidos y límites que podrían degradar el servicio."""
    response = client.post("/analizar-conflicto", json=payload)

    assert response.status_code == 422
