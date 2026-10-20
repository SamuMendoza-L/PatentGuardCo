import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError


class DisputeAnalysisSchema(BaseModel):
    resumen: str = Field(description="Resumen objetivo del análisis de la disputa.")
    hechos_verificados: List[str] = Field(description="Datos y hechos verificables extraídos del registro oficial.")
    inconsistencias: List[str] = Field(description="Inconsistencias técnicas o formales identificadas.")
    informacion_faltante: List[str] = Field(description="Datos no presentes o registros omitidos que impiden la verificación completa.")
    analisis_etico: Dict[str, str] = Field(
        description="Evaluación de riesgos éticos por falta de reconocimiento de autoría, análisis del dilema Autoría vs Lucro y un descargo legal."
    )
    recomendaciones: List[str] = Field(description="Recomendaciones para la verificación objetiva de la disputa.")


class GeminiServiceError(Exception):
    """Excepción personalizada para errores del servicio de Gemini."""
    pass


def _get_client() -> genai.Client:
    """Inicializa el cliente oficial de Gemini comprobando la API Key en las variables de entorno."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiServiceError("La variable de entorno 'GEMINI_API_KEY' no está configurada.")
    return genai.Client(api_key=api_key)


def evaluar_disputa_con_gemini(
    datos_patente: Dict[str, Any],
    inconsistencias_tecnicas: List[str],
    inventores_reclamantes: Optional[List[str]] = None,
    client: Optional[genai.Client] = None
) -> Dict[str, Any]:
    """
    Analiza una disputa de autoría de patentes usando el SDK de Gemini (google-genai).
    Produce un análisis estructurado sin afirmar culpabilidades ni validez legal.
    """
    if client is None:
        client = _get_client()

    prompt = f"""
    Actúa como un perito técnico y ético en Calidad de Software y Propiedad Intelectual.
    Analiza la siguiente información de un registro de patente y sus inconsistencias asociadas.

    === DATOS DE LA PATENTE ===
    {json.dumps(datos_patente, ensure_ascii=False, indent=2)}

    === INCONSISTENCIAS TÉCNICAS DETECTADAS ===
    {json.dumps(inconsistencias_tecnicas, ensure_ascii=False, indent=2)}

    === INVENTORES/DESARROLLADORES RECLAMANTES ===
    {json.dumps(inventores_reclamantes or ["No especificados"], ensure_ascii=False, indent=2)}

    INSTRUCCIONES DE EVALUACIÓN:
    1. Basate estrictamente en hechos documentados e inconsistencias detectadas. NO inventes datos.
    2. En el análisis ético, aborda los riesgos por falta de reconocimiento de autoría y responde formalmente la pregunta central: "¿Qué es más importante, la autoría o el lucro?"
    3. NO afirmes culpabilidad, fraude ni responsabilidad legal. Aclara explícitamente en el descargo legal que esto es una evaluación de calidad de software y no un dictamen judicial vinculante.
    """

    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DisputeAnalysisSchema,
            temperature=0.2,
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        if not response.text:
            raise GeminiServiceError("La API de Gemini devolvió una respuesta vacía.")

        # Devuelve el dict parseado desde el JSON estructurado
        return json.loads(response.text)

    except APIError as e:
        if "401" in str(e) or "API_KEY_INVALID" in str(e):
            raise GeminiServiceError("Error de autenticación: API Key de Gemini inválida.")
        elif "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise GeminiServiceError("Límite de cuota excedido para la API de Gemini (Rate limit).")
        elif "503" in str(e) or "UNAVAILABLE" in str(e):
            raise GeminiServiceError("El servicio de Gemini API no está disponible temporalmente.")
        else:
            raise GeminiServiceError(f"Error de la API de Gemini: {str(e)}")
    except json.JSONDecodeError as e:
        raise GeminiServiceError(f"Respuesta inválida recibida de Gemini (Error al parsear JSON): {str(e)}")
    except Exception as e:
        raise GeminiServiceError(f"Error inesperado al procesar la evaluación con Gemini: {str(e)}")