import pytest
from unittest.mock import patch, MagicMock
import httpx
from app.client_datos_abiertos import (
    consultar_patente_por_numero_solicitud,
    DatosAbiertosAPIError
)


@pytest.mark.asyncio
async def test_consultar_patente_exitoso():
    """Verifica que retorne los datos estructurados correctamente ante una respuesta HTTP 200 OK."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = [
        {
            "numero_solicitud": "NC2026/000123",
            "titulo_resumen": "Sistema de Trazabilidad Algorítmica",
            "solicitante": "Universidad Tecnológica",
            "inventor": "Samuel Mendoza, Andrés Felipe",
            "fecha_radicacion": "2026-01-15T00:00:00.000",
            "estado": "Publicada"
        }
    ]

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        resultado = await consultar_patente_por_numero_solicitud("NC2026/000123")

    assert resultado is not None
    assert resultado["numero_solicitud"] == "NC2026/000123"
    assert resultado["solicitante"] == "Universidad Tecnológica"
    assert resultado["inventor"] == "Samuel Mendoza, Andrés Felipe"


@pytest.mark.asyncio
async def test_consultar_patente_no_encontrada():
    """Verifica que retorne None cuando la API responde con una lista vacía."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = []

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        resultado = await consultar_patente_por_numero_solicitud("INEXISTENTE-999")

    assert resultado is None


@pytest.mark.asyncio
async def test_manejo_error_http():
    """Verifica la captura y transformación de un error HTTP (ej. 500 o 404)."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=MagicMock(status_code=500))):
        with pytest.raises(DatosAbiertosAPIError) as exc_info:
            await consultar_patente_por_numero_solicitud("NC2026/000123")
        
        assert "Error HTTP 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_manejo_timeout():
    """Verifica que el agotamiento del tiempo de espera genere la excepción DatosAbiertosAPIError."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout err")):
        with pytest.raises(DatosAbiertosAPIError) as exc_info:
            await consultar_patente_por_numero_solicitud("NC2026/000123")
        
        assert "Tiempo de espera agotado" in str(exc_info.value)


@pytest.mark.asyncio
async def test_manejo_json_invalido():
    """Verifica la excepción cuando la API devuelve un contenido no parseable a JSON."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError("JSONDecodeError")

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        with pytest.raises(DatosAbiertosAPIError) as exc_info:
            await consultar_patente_por_numero_solicitud("NC2026/000123")

        assert "JSON válido" in str(exc_info.value)