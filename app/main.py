import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, status

from app.schemas import ConflictAnalysisRequest, ConflictAnalysisResponse
from app.client_datos_abiertos import consultar_patente_por_numero_solicitud, DatosAbiertosAPIError
from app.validator import validate_single_patent_record, validate_patent_dataset
from app.gemini_service import evaluar_disputa_con_gemini, GeminiServiceError

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="API de Integridad y Evaluación de Patentes",
    description="Microservicio académico para Calidad de Software que combina Datos Abiertos de Colombia, validación determinista de datos y evaluación ética con Gemini.",
    version="1.0.0"
)


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    """Indica que el servicio está activo y expone sus rutas de consulta básica."""
    return {
        "message": "API de Integridad y Evaluación de Patentes activa",
        "documentation": "/docs",
        "health_check": "/health",
    }


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "ok",
        "message": "Servicio de Evaluación de Patentes y Calidad de Software operativo"
    }


@app.post("/analizar-conflicto", response_model=ConflictAnalysisResponse, status_code=status.HTTP_200_OK)
async def analizar_conflicto_patente(payload: ConflictAnalysisRequest):
    registros_encontrados: List[Dict[str, Any]] = []
    solicitudes_no_encontradas: List[str] = []
    inconsistencias_unificadas: List[str] = []
    limitaciones: List[str] = [
        "Las similitudes entre resúmenes de código o títulos no constituyen prueba de plagio o infracción legal por sí solas.",
        "El análisis generado por Gemini API es puramente cualitativo/académico y no constituye un dictamen ni peritaje judicial vinculante."
    ]

    # 1. Ingesta de Datos Abiertos para cada número de solicitud
    for num_sol in payload.numeros_solicitud:
        try:
            patente = await consultar_patente_por_numero_solicitud(num_sol.strip())
            if patente:
                registros_encontrados.append(patente)
            else:
                solicitudes_no_encontradas.append(num_sol)
        except DatosAbiertosAPIError as err:
            logger.warning(f"Error consultando datos.gov.co para {num_sol}: {err}")
            limitaciones.append(f"No se pudo verificar en tiempo real la solicitud '{num_sol}': {str(err)}")

    if solicitudes_no_encontradas:
        limitaciones.append(f"Las siguientes solicitudes no fueron localizadas en el dataset público: {solicitudes_no_encontradas}")

    # 2. Validación Determinista de Integridad
    if registros_encontrados:
        dataset_eval = validate_patent_dataset(registros_encontrados)
        inconsistencias_unificadas.extend(dataset_eval.get("dataset_errors", []))

        for rec_eval in dataset_eval.get("records_evaluations", []):
            eval_data = rec_eval.get("evaluation", {})
            sol_id = rec_eval.get("numero_solicitud", "Desconocido")
            
            for err in eval_data.get("errors", []):
                inconsistencias_unificadas.append(f"[{sol_id}] Error: {err}")
            for warn in eval_data.get("warnings", []):
                inconsistencias_unificadas.append(f"[{sol_id}] Advertencia: {warn}")
            for anom in eval_data.get("anomalies", []):
                inconsistencias_unificadas.append(f"[{sol_id}] Anomalía: {anom}")

    # 3. Evaluación Cualitativa Ética con Gemini
    evaluacion_gemini = None
    if not registros_encontrados:
        limitaciones.append("Información insuficiente para que Gemini realice un análisis ético detallado (no se encontraron registros de patentes válidos).")
    else:
        try:
            contexto_patente = {
                "descripcion_conflicto_usuario": payload.descripcion_conflicto,
                "patentes_consultadas": registros_encontrados
            }
            evaluacion_gemini = evaluar_disputa_con_gemini(
                datos_patente=contexto_patente,
                inconsistencias_tecnicas=inconsistencias_unificadas,
                inventores_reclamantes=payload.inventores_reclamantes
            )
        except GeminiServiceError as err:
            logger.error(f"Fallo en el servicio Gemini API: {err}")
            limitaciones.append(f"Evaluación ética con Gemini no disponible temporalmente: {str(err)}")

    status_code = "success" if registros_encontrados and evaluacion_gemini else "partial_success"

    return ConflictAnalysisResponse(
        status=status_code,
        resumen_procesamiento={
            "solicitudes_consultadas": len(payload.numeros_solicitud),
            "registros_encontrados": len(registros_encontrados),
            "solicitudes_no_encontradas": len(solicitudes_no_encontradas),
            "total_inconsistencias_detectadas": len(inconsistencias_unificadas)
        },
        registros_encontrados=registros_encontrados,
        inconsistencias_tecnicas=inconsistencias_unificadas,
        analisis_etico_gemini=evaluacion_gemini,
        limitaciones_y_advertencias=limitaciones
    )
