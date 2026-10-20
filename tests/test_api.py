import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verifica que el servicio responda correctamente en la ruta /health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("app.main.consultar_patente_por_numero_solicitud", new_callable=AsyncMock)
@patch("app.main.evaluar_disputa_con_gemini")
def test_analizar_conflicto_exitoso(mock_gemini, mock_datos_abiertos):
    """Prueba el flujo exitoso integrando mocks de la red externa."""
    # Mockear respuesta de datos.gov.co
    mock_datos_abiertos.return_value = {
        "numero_solicitud": "NC2026/000123",
        "titulo": "Sistema Algorítmico de Trazabilidad",
        "solicitante": "Universidad Tecnológica",
        "inventor": None,  # Generará una advertencia de falta de inventor
        "fecha_radicacion": "2026-01-10T00:00:00.000",
        "estado": "Publicada"
    }

    # Mockear respuesta de Gemini API
    mock_gemini.return_value = {
        "resumen": "Resumen mock del conflicto de autoría presentado por Samuel Mendoza y Andrés Felipe.",
        "hechos_verificados": ["Patente NC2026/000123 registrada."],
        "inconsistencias": ["Ausencia de registro del campo 'inventor'."],
        "informacion_faltante": ["Bitácora de autoría original."],
        "analisis_etico": {
            "riesgo_etico": "Posible omisión de derecho moral de autoría.",
            "autoria_vs_lucro": "La autoría es primordial como derecho moral inalienable.",
            "descargo_legal": "Evaluación orientativa académica no vinculante."
        },
        "recomendaciones": ["Verificar actas de desarrollo."]
    }

    payload = {
        "numeros_solicitud": ["NC2026/000123"],
        "descripcion_conflicto": "Disputa de autoría presentada por los desarrolladores principales Samuel Mendoza y Andrés Felipe.",
        "inventores_reclamantes": ["Samuel Mendoza", "Andrés Felipe"]
    }

    response = client.post("/analizar-conflicto", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["resumen_procesamiento"]["registros_encontrados"] == 1
    assert data["analisis_etico_gemini"] is not None
    assert "Samuel Mendoza" in str(data["analisis_etico_gemini"])


def test_analizar_conflicto_payload_invalido():
    """Verifica que la API rechace solicitudes con datos mal formados mediante FastAPI/Pydantic."""
    payload = {
        "numeros_solicitud": [],  # Lista vacía no permitida (min_items=1)
        "descripcion_conflicto": "Corta"  # Menos de 10 caracteres
    }

    response = client.post("/analizar-conflicto", json=payload)
    assert response.status_code == 422  # Unprocessable Entity
