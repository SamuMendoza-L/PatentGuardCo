import asyncio
import logging
from contextlib import asynccontextmanager
from time import perf_counter
from typing import List, Dict, Any, Optional
import httpx
from fastapi import FastAPI, status
from cachetools import TTLCache

from app.schemas import ConflictAnalysisRequest, ConflictAnalysisResponse
from app.client_datos_abiertos import consultar_patente_por_numero_solicitud, DatosAbiertosAPIError
from app.validator import validate_single_patent_record, validate_patent_dataset
from app.gemini_service import evaluar_disputa_con_gemini, GeminiServiceError
from app.jev_service import evaluar_decision_jev

logger = logging.getLogger("uvicorn.error")

# Optimización 3: Caché TTL en memoria para respuestas completas de evaluación (512 entradas, 5 min)
evaluaciones_endpoint_cache: TTLCache = TTLCache(maxsize=512, ttl=300)


# Optimización 1: Ciclo de vida lifespan con Connection Pooling global
@asynccontextmanager
async def lifespan(app_instancia: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    Inicializa un httpx.AsyncClient con límites de conexión configurados para reutilización
    de sockets TCP y keep-alive, evitando el sobrecosto de handshakes en cada petición.
    """
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    client = httpx.AsyncClient(limits=limits, timeout=10.0)
    app_instancia.state.http_client = client
    logger.info("Connection pool global inicializado (max_keepalive=20, max_connections=50).")
    yield
    await client.aclose()
    logger.info("Connection pool global cerrado correctamente.")


app = FastAPI(
    title="API de Integridad y Evaluación de Patentes",
    description="Microservicio para Calidad de Software con Datos Abiertos de Colombia, validación determinista, y evaluación con JEV y Gemini.",
    version="1.1.0",
    lifespan=lifespan,
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
    inicio_procesamiento = perf_counter()

    # Optimización 1: Obtener el cliente HTTP del pool global si la app corre en lifespan
    http_client: Optional[httpx.AsyncClient] = getattr(app.state, "http_client", None)

    # Optimización 3: Verificación de clave compuesta en caché TTL si el pool está activo (producción/carga)
    cache_key = (
        tuple(sorted(payload.numeros_solicitud)),
        payload.descripcion_conflicto,
        tuple(sorted(payload.inventores_reclamantes or []))
    )
    if http_client is not None and cache_key in evaluaciones_endpoint_cache:
        return evaluaciones_endpoint_cache[cache_key]

    registros_encontrados: List[Dict[str, Any]] = []
    solicitudes_no_encontradas: List[str] = []
    inconsistencias_unificadas: List[str] = []
    limitaciones: List[str] = [
        "Las similitudes entre resúmenes de código o títulos no constituyen prueba de plagio o infracción legal por sí solas.",
        "El análisis generado por Gemini API es puramente cualitativo/académico y no constituye un dictamen ni peritaje judicial vinculante."
    ]

    # Optimización 2: Ingesta concurrente de patentes usando asyncio.gather
    async def _consultar_seguro(num_sol: str):
        num_clean = num_sol.strip()
        try:
            patente = await consultar_patente_por_numero_solicitud(num_clean, client=http_client)
            return (num_clean, patente, None)
        except DatosAbiertosAPIError as err:
            logger.warning("No fue posible consultar datos.gov.co para una solicitud: %s", err)
            return (num_clean, None, err)

    tareas_consulta = [_consultar_seguro(num) for num in payload.numeros_solicitud]
    resultados_consultas = await asyncio.gather(*tareas_consulta)

    hubo_error_proveedor = False
    for num_clean, patente, error in resultados_consultas:
        if patente:
            registros_encontrados.append(patente)
        elif error is None:
            solicitudes_no_encontradas.append(num_clean)
        else:
            hubo_error_proveedor = True

    if hubo_error_proveedor:
        limitaciones.append("No fue posible verificar una solicitud en tiempo real por un error del proveedor de datos abiertos.")

    if solicitudes_no_encontradas:
        limitaciones.append(f"Las siguientes solicitudes no fueron localizadas en el dataset público: {solicitudes_no_encontradas}")

    # 2. Validación Determinista de Integridad (Optimización 4: O(1) hashing y regex precompiladas)
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

    # 3. Evaluación con Modelos de Decisión JEV (Optimización 4: Primitivas Choice & Score) y Gemini
    evaluacion_gemini = None
    evaluacion_jev = None

    if not registros_encontrados:
        limitaciones.append("Información insuficiente para que Gemini realice un análisis ético detallado (no se encontraron registros de patentes válidos).")
    else:
        contexto_patente = {
            "descripcion_conflicto_usuario": payload.descripcion_conflicto,
            "patentes_consultadas": registros_encontrados
        }

        # 3A. Evaluación con Modelo de Decisión JEV (local Ollama qwen3:1.7b con fallback determinista)
        try:
            evaluacion_jev = await evaluar_decision_jev(
                datos_patente=contexto_patente,
                inconsistencias_tecnicas=inconsistencias_unificadas,
                inventores_reclamantes=payload.inventores_reclamantes,
                client=http_client
            )
        except Exception as exc:
            logger.warning("No se pudo completar la evaluación JEV: %s", exc)

        # 3B. Evaluación Cualitativa Ética con Gemini
        try:
            evaluacion_gemini = evaluar_disputa_con_gemini(
                datos_patente=contexto_patente,
                inconsistencias_tecnicas=inconsistencias_unificadas,
                inventores_reclamantes=payload.inventores_reclamantes
            )
        except GeminiServiceError:
            logger.error("La evaluación ética con Gemini no está disponible temporalmente.")
            limitaciones.append("Evaluación ética con Gemini no disponible temporalmente.")

    status_code = "success" if registros_encontrados and (evaluacion_gemini or evaluacion_jev) else "partial_success"
    tiempo_procesamiento_ms = round((perf_counter() - inicio_procesamiento) * 1000, 2)

    respuesta = ConflictAnalysisResponse(
        status=status_code,
        resumen_procesamiento={
            "solicitudes_consultadas": len(payload.numeros_solicitud),
            "registros_encontrados": len(registros_encontrados),
            "solicitudes_no_encontradas": len(solicitudes_no_encontradas),
            "total_inconsistencias_detectadas": len(inconsistencias_unificadas),
            "tiempo_procesamiento_ms": tiempo_procesamiento_ms,
        },
        registros_encontrados=registros_encontrados,
        solicitudes_no_encontradas=solicitudes_no_encontradas,
        inconsistencias_tecnicas=inconsistencias_unificadas,
        analisis_etico_gemini=evaluacion_gemini,
        decision_jev=evaluacion_jev,
        limitaciones_y_advertencias=limitaciones
    )

    # Almacenar en caché de evaluación cuando el pool está activo
    if http_client is not None:
        evaluaciones_endpoint_cache[cache_key] = respuesta

    return respuesta
