from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ConflictAnalysisRequest(BaseModel):
    numeros_solicitud: List[str] = Field(
        ...,
        min_items=1,
        description="Lista de identificadores o números de solicitud de patente a consultar.",
        example=["NC2026/000123", "NC2026/000456"]
    )
    descripcion_conflicto: str = Field(
        ...,
        min_length=10,
        description="Descripción contextual de la disputa de autoría o alegato.",
        example="Samuel Mendoza y Andrés Felipe figuran como desarrolladores originales, pero el registro solo lista a la entidad jurídica como titular."
    )
    inventores_reclamantes: Optional[List[str]] = Field(
        default=None,
        description="Nombres de los desarrolladores o inventores que reclaman la autoría moral.",
        example=["Samuel Mendoza", "Andrés Felipe"]
    )


class ConflictAnalysisResponse(BaseModel):
    status: str = Field(..., description="Estado de la ejecución ('success', 'partial_success', 'error').")
    resumen_procesamiento: Dict[str, Any] = Field(..., description="Métricas de registros consultados y hallazgos.")
    registros_encontrados: List[Dict[str, Any]] = Field(..., description="Lista de patentes recuperadas de datos.gov.co.")
    inconsistencias_tecnicas: List[str] = Field(..., description="Lista unificada de fallas o inconsistencias detectadas por reglas deterministas.")
    analisis_etico_gemini: Optional[Dict[str, Any]] = Field(default=None, description="Evaluación cualitativa y ética producida por Gemini API.")
    limitaciones_y_advertencias: List[str] = Field(..., description="Descargos de responsabilidad y notas metodológicas.")