from typing import Dict, Any, List, Set
from datetime import datetime


class PatentValidationResult:
    """Estructura del resultado de validación de integridad."""
    def __init__(self, is_valid: bool, errors: List[str], warnings: List[str], anomalies: List[str]):
        self.is_valid = is_valid
        self.errors = errors          # Campos obligatorios ausentes o corruptos
        self.warnings = warnings      # Campos recomendados ausentes
        self.anomalies = anomalies    # Anomalías de tipos, fechas incoherentes o duplicados

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "anomalies": self.anomalies
        }


def validate_single_patent_record(record: Dict[str, Any]) -> PatentValidationResult:
    """
    Valida la integridad técnica de un único registro de patente.
    Distingue entre campos obligatorios, recomendados y anomalías de datos.
    """
    errors: List[str] = []
    warnings: List[str] = []
    anomalies: List[str] = []

    if not isinstance(record, dict):
        return PatentValidationResult(
            is_valid=False,
            errors=["El registro proporcionado no es un diccionario válido."],
            warnings=[],
            anomalies=[]
        )

    # 1. Validación de Campos Obligatorios
    num_solicitud = record.get("numero_solicitud")
    if not num_solicitud or not str(num_solicitud).strip():
        errors.append("Campo obligatorio ausente o vacío: 'numero_solicitud'.")
    elif not isinstance(num_solicitud, str):
        anomalies.append(f"Tipo de dato inesperado para 'numero_solicitud': se esperaba 'str', se obtuvo '{type(num_solicitud).__name__}'.")

    titulo = record.get("titulo")
    if not titulo or not str(titulo).strip():
        errors.append("Campo obligatorio ausente o vacío: 'titulo'.")
    elif not isinstance(titulo, str):
        anomalies.append(f"Tipo de dato inesperado para 'titulo': se esperaba 'str', se obtuvo '{type(titulo).__name__}'.")

    # 2. Validación de Campos Recomendados (Trazabilidad)
    solicitante = record.get("solicitante")
    if not solicitante or not str(solicitante).strip():
        warnings.append("Campo recomendado ausente: 'solicitante' (entidad o titular registrado).")
    elif not isinstance(solicitante, str):
        anomalies.append(f"Tipo de dato inesperado para 'solicitante': se esperaba 'str', se obtuvo '{type(solicitante).__name__}'.")

    inventor = record.get("inventor")
    if not inventor or not str(inventor).strip():
        warnings.append("Campo recomendado ausente: 'inventor' (autores o creadores no registrados en la ficha).")
    elif not isinstance(inventor, str):
        anomalies.append(f"Tipo de dato inesperado para 'inventor': se esperaba 'str', se obtuvo '{type(inventor).__name__}'.")

    # 3. Validación de Fechas y Anomalías Temporales
    fecha_rad = _parse_date(record.get("fecha_radicacion"), "fecha_radicacion", anomalies)
    fecha_pub = _parse_date(record.get("fecha_publicacion"), "fecha_publicacion", anomalies)

    if fecha_rad and fecha_pub:
        if fecha_pub < fecha_rad:
            anomalies.append(f"Inconsistencia temporal: La fecha de publicación ({fecha_pub.strftime('%Y-%m-%d')}) es anterior a la fecha de radicación ({fecha_rad.strftime('%Y-%m-%d')}).")

    # Validación específica de año de publicación si viene explicitado
    anio_pub = record.get("anio_publicacion")
    if anio_pub is not None:
        if isinstance(anio_pub, int):
            if anio_pub < 1800 or anio_pub > 2100:
                anomalies.append(f"Año de publicación fuera de rango razonable: {anio_pub}.")
        else:
            anomalies.append(f"Tipo de dato incorrecto para 'anio_publicacion': se esperaba 'int', se obtuvo '{type(anio_pub).__name__}'.")

    is_valid = len(errors) == 0
    return PatentValidationResult(is_valid, errors, warnings, anomalies)


def validate_patent_dataset(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Valida un conjunto completo de registros de patentes y detecta duplicados.
    """
    if not isinstance(records, list):
        return {
            "total_records": 0,
            "valid_records_count": 0,
            "dataset_errors": ["El conjunto de datos debe ser una lista de registros."],
            "records_evaluations": []
        }

    seen_solicitudes: Set[str] = set()
    duplicate_solicitudes: Set[str] = set()
    evaluations: List[Dict[str, Any]] = []
    valid_count = 0

    for idx, rec in enumerate(records):
        val_res = validate_single_patent_record(rec)
        if val_res.is_valid:
            valid_count += 1

        # Detección de solicitudes duplicadas
        num_sol = rec.get("numero_solicitud") if isinstance(rec, dict) else None
        if isinstance(num_sol, str) and num_sol.strip():
            num_clean = num_sol.strip()
            if num_clean in seen_solicitudes:
                duplicate_solicitudes.add(num_clean)
                val_res.anomalies.append(f"Solicitud duplicada detectada en la posición {idx}: '{num_clean}'.")
            else:
                seen_solicitudes.add(num_clean)

        evaluations.append({
            "record_index": idx,
            "numero_solicitud": num_sol,
            "evaluation": val_res.to_dict()
        })

    dataset_errors = []
    if duplicate_solicitudes:
        dataset_errors.append(f"Se encontraron solicitudes duplicadas en el dataset: {list(duplicate_solicitudes)}")

    return {
        "total_records": len(records),
        "valid_records_count": valid_count,
        "dataset_errors": dataset_errors,
        "records_evaluations": evaluations
    }


def _parse_date(date_val: Any, field_name: str, anomalies: List[str]) -> Any:
    """Auxiliar para parsear y validar campos de fecha."""
    if not date_val:
        return None
    
    if not isinstance(date_val, str):
        anomalies.append(f"Tipo de dato inesperado para '{field_name}': se esperaba 'str', se obtuvo '{type(date_val).__name__}'.")
        return None

    # Admite timestamps ISO de Socrata y el formato DD/MM/AAAA del recurso de patentes.
    clean_date_str = date_val.split("T")[0]
    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(clean_date_str, date_format)
        except ValueError:
            continue

    anomalies.append(
        f"Formato de fecha inválido en '{field_name}': '{date_val}'. "
        "Se esperaba YYYY-MM-DD o DD/MM/AAAA."
    )
    return None
