import httpx
from typing import Dict, Any, Optional

BASE_URL_DATOS_GOV = "https://www.datos.gov.co/resource/9n7g-3red.json"
DEFAULT_TIMEOUT = 10.0  # Tiempo límite en segundos


class DatosAbiertosAPIError(Exception):
    """Excepción personalizada para errores al consumir la API de Datos Abiertos."""
    pass


async def consultar_patente_por_numero_solicitud(
    numero_solicitud: str,
    base_url: str = BASE_URL_DATOS_GOV,
    timeout: float = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """
    Consulta la API pública de datos.gov.co buscando por número de solicitud.
    Aplica filtro SoQL ($where) para evitar descargar el dataset completo.
    """
    # Consulta optimizada mediante parámetros Socrata
    params = {
        "$where": f"solicitud = '{numero_solicitud}'",
        "$limit": 1
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                raise DatosAbiertosAPIError("El formato devuelto por la API no es una lista válida.")
                
            if not data:
                return None  # No se encontró ninguna patente con ese número
                
            raw_record = data[0]
            
            # Estructuración limpia del registro
            return {
                "numero_solicitud": (
                    raw_record.get("solicitud")
                    or raw_record.get("numero_solicitud")
                    or numero_solicitud
                ),
                "titulo": raw_record.get("titulo_resumen") or raw_record.get("titulo", "Sin título"),
                "solicitante": raw_record.get("solicitante") or raw_record.get("titular", "Desconocido"),
                "inventor": raw_record.get("inventor") or raw_record.get("inventores", None),
                "fecha_radicacion": raw_record.get("fecha_radicacion"),
                "fecha_publicacion": raw_record.get("fecha_de_publicacion") or raw_record.get("fecha_publicacion"),
                "estado": raw_record.get("estado") or raw_record.get("fase") or raw_record.get("tr_mite", "En trámite"),
                "raw_data": raw_record
            }

    except httpx.TimeoutException as err:
        raise DatosAbiertosAPIError(f"Tiempo de espera agotado al conectar con datos.gov.co: {err}")
    except httpx.HTTPStatusError as err:
        raise DatosAbiertosAPIError(f"Error HTTP {err.response.status_code} devuelto por datos.gov.co.")
    except httpx.RequestError as err:
        raise DatosAbiertosAPIError(f"Error de red o conexión al consultar datos.gov.co: {err}")
    except ValueError as err:
        raise DatosAbiertosAPIError(f"La respuesta recibida no es un JSON válido: {err}")
