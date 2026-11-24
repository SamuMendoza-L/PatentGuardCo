"""
Módulo de Integración con Modelo de Decisión JEV (TypeSafe / Ollama).
Aplica los conceptos de 'charla-jev' para clasificar disputas de autoría con
primitivas tipadas:
  - Primitiva Choice: Clasificación categórica del conflicto con nivel de confianza.
  - Primitiva Score: Índice continuo/ordinal de severidad y mérito técnico (1.0 a 5.0).
  - Primitiva Action: Determinación de triage según umbral de corte.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from cachetools import TTLCache

logger = logging.getLogger("uvicorn.error")

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_LOCAL_MODEL = "qwen3:1.7b"

# Optimización 3: Caché TTL en memoria para decisiones de JEV (512 entradas, 5 minutos TTL)
decision_cache: TTLCache = TTLCache(maxsize=512, ttl=300)

# Esquema JSON estructurado estricto para las primitivas de decisión
JEV_DECISION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "tipo_conflicto": {
            "type": "string",
            "enum": [
                "OMISION_FORMAL",
                "DISPUTA_AUTORIA_DIRECTA",
                "INCONSISTENCIA_TEMPORAL",
                "SIN_EVIDENCIA_SUFICIENTE"
            ]
        },
        "confianza_tipo": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "score_severidad": {
            "type": "number",
            "minimum": 1.0,
            "maximum": 5.0
        },
        "accion_recomendada": {
            "type": "string",
            "enum": [
                "REVISION_PRIORITARIA",
                "AUDITORIA_DOCUMENTAL",
                "DESESTIMAR"
            ]
        },
        "requiere_peritaje": {
            "type": "boolean"
        },
        "justificacion_breve": {
            "type": "string"
        }
    },
    "required": [
        "tipo_conflicto",
        "confianza_tipo",
        "score_severidad",
        "accion_recomendada",
        "requiere_peritaje",
        "justificacion_breve"
    ]
}


def _generar_decision_deterministica(
    datos_patente: Dict[str, Any],
    inconsistencias_tecnicas: List[str],
    inventores_reclamantes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Motor determinista de respaldo (fallback) basado en reglas de corte de la charla JEV.
    Garantiza disponibilidad ininterrumpida y ejecución instantánea en pruebas unitarias.
    """
    reclamantes = inventores_reclamantes or []
    tiene_inconsistencias = len(inconsistencias_tecnicas) > 0
    tiene_reclamantes = len(reclamantes) > 0
    
    # Análisis de inconsistencias temporales
    hay_anomalia_temporal = any("temporal" in inc.lower() or "fecha" in inc.lower() for inc in inconsistencias_tecnicas)

    if tiene_reclamantes and tiene_inconsistencias:
        tipo = "DISPUTA_AUTORIA_DIRECTA"
        confianza = 0.90
        score = 4.2
        accion = "REVISION_PRIORITARIA"
        peritaje = True
        justificacion = "Coincidencia de reclamantes formales con inconsistencias técnicas no resueltas en la ficha de patente."
    elif hay_anomalia_temporal:
        tipo = "INCONSISTENCIA_TEMPORAL"
        confianza = 0.85
        score = 3.5
        accion = "AUDITORIA_DOCUMENTAL"
        peritaje = True
        justificacion = "Inconsistencias en fechas de radicación o publicación que requieren verificación documental."
    elif tiene_inconsistencias:
        tipo = "OMISION_FORMAL"
        confianza = 0.80
        score = 2.5
        accion = "AUDITORIA_DOCUMENTAL"
        peritaje = False
        justificacion = "Faltan campos recomendados o existen anomalías formales sin alegato directo de inventores."
    else:
        tipo = "SIN_EVIDENCIA_SUFICIENTE"
        confianza = 0.70
        score = 1.0
        accion = "DESESTIMAR"
        peritaje = False
        justificacion = "Registro sin inconsistencias técnicas ni mérito evidente de disputa preliminar."

    return {
        "tipo_conflicto": tipo,
        "confianza_tipo": confianza,
        "score_severidad": score,
        "accion_recomendada": accion,
        "requiere_peritaje": peritaje,
        "justificacion_breve": justificacion,
        "proveedor": "JEV_DETERMINISTIC_RULES"
    }


async def evaluar_decision_jev(
    datos_patente: Dict[str, Any],
    inconsistencias_tecnicas: List[str],
    inventores_reclamantes: Optional[List[str]] = None,
    client: Optional[httpx.AsyncClient] = None,
    timeout: float = 3.0
) -> Dict[str, Any]:
    """
    Evalúa una disputa de autoría utilizando el modelo de decisión JEV (local vía Ollama qwen3:1.7b).
    Aplica Connection Pooling si se provee `client` y Caché TTL para no repetir inferencias idénticas.
    En entornos de prueba (sin cliente de pool), ejecuta el motor determinista de alta velocidad.
    """
    if client is None:
        return _generar_decision_deterministica(
            datos_patente=datos_patente,
            inconsistencias_tecnicas=inconsistencias_tecnicas,
            inventores_reclamantes=inventores_reclamantes
        )

    # Clave de caché basada en hash de entrada
    patentes_consultadas = datos_patente.get("patentes_consultadas", [])
    num_sols = sorted([p.get("numero_solicitud", "") for p in patentes_consultadas if isinstance(p, dict)])
    cache_key = f"{','.join(num_sols)}|{','.join(sorted(inventores_reclamantes or []))}|{len(inconsistencias_tecnicas)}"

    if cache_key in decision_cache:
        return decision_cache[cache_key]

    prompt = f"""
    Evalúa la siguiente disputa de patentes y emite una decisión técnica tipada con base en los hechos:
    - Patentes: {json.dumps(datos_patente, ensure_ascii=False)}
    - Inconsistencias: {json.dumps(inconsistencias_tecnicas, ensure_ascii=False)}
    - Reclamantes: {json.dumps(inventores_reclamantes or [], ensure_ascii=False)}
    """

    payload = {
        "model": DEFAULT_LOCAL_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Eres un modelo de decisión técnica (JEV Decision Engine). Evalúa la evidencia y responde estrictamente con el JSON Schema especificado."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "format": JEV_DECISION_JSON_SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }

    try:
        url = f"{OLLAMA_URL}/api/chat"
        resp = await client.post(url, json=payload, timeout=timeout)

        if resp.status_code == 200:
            data = resp.json()
            raw_content = data.get("message", {}).get("content", "")
            decision = json.loads(raw_content)
            decision["proveedor"] = f"JEV_LOCAL_OLLAMA_{DEFAULT_LOCAL_MODEL}"
            decision_cache[cache_key] = decision
            return decision

    except Exception as exc:
        logger.warning("Fallo o timeout al consultar Ollama local para JEV (%s). Activando fallback determinista.", exc)

    # Fallback determinista cuando Ollama está ocupado o apagado
    decision_fallback = _generar_decision_deterministica(
        datos_patente=datos_patente,
        inconsistencias_tecnicas=inconsistencias_tecnicas,
        inventores_reclamantes=inventores_reclamantes
    )
    decision_cache[cache_key] = decision_fallback
    return decision_fallback
