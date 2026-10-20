import pytest
from app.validator import (
    validate_single_patent_record,
    validate_patent_dataset
)


# 1. Caso Válido
def test_valid_patent_record():
    """Registro con todos los campos bien formateados debe ser totalmente válido."""
    record = {
        "numero_solicitud": "NC2026/000100",
        "titulo": "Sistema de Cifrado Cuántico",
        "solicitante": "Universidad Tecnológica",
        "inventor": "Samuel Mendoza, Andrés Felipe",
        "fecha_radicacion": "2025-05-10T00:00:00.000",
        "fecha_publicacion": "2026-01-15T00:00:00.000",
        "anio_publicacion": 2026
    }
    result = validate_single_patent_record(record)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    assert len(result.anomalies) == 0


# 2. Casos Inválidos (Campos Obligatorios Ausentes)
def test_missing_mandatory_fields():
    """Falta de numero_solicitud y titulo debe marcar el registro como inválido."""
    record = {
        "solicitante": "Empresa X",
        "inventor": "Samuel Mendoza"
    }
    result = validate_single_patent_record(record)
    assert result.is_valid is False
    assert any("numero_solicitud" in err for err in result.errors)
    assert any("titulo" in err for err in result.errors)


# 3. Campos Recomendados Ausentes (Inventores/Solicitantes)
def test_missing_recommended_fields():
    """Falta de inventor y solicitante genera advertencias pero no invalida si el título y solicitud existen."""
    record = {
        "numero_solicitud": "NC2026/000101",
        "titulo": "Dispositivo Bio-médico",
        "solicitante": "",
        "inventor": None
    }
    result = validate_single_patent_record(record)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 2
    assert any("solicitante" in warn for warn in result.warnings)
    assert any("inventor" in warn for warn in result.warnings)


# 4. Tipos Inesperados y Fechas Invalidadas
def test_unexpected_data_types_and_date_anomalies():
    """Soporta la detección de tipos erróneos y fechas incoherentes (publicación anterior a radicación)."""
    record = {
        "numero_solicitud": "NC2026/000102",
        "titulo": "Motor Stirling Optimizado",
        "solicitante": 12345,  # Tipo int en lugar de str
        "inventor": "Andrés Felipe",
        "fecha_radicacion": "2026-05-01T00:00:00.000",
        "fecha_publicacion": "2025-01-01T00:00:00.000",  # Publicación previa a radicación
        "anio_publicacion": "DOS_MIL_VEINTISEIS"  # Tipo str en lugar de int
    }
    result = validate_single_patent_record(record)
    assert result.is_valid is True  # Mantiene is_valid si tiene campos obligatorios
    assert any("solicitante" in anom for anom in result.anomalies)
    assert any("Inconsistencia temporal" in anom for anom in result.anomalies)
    assert any("anio_publicacion" in anom for anom in result.anomalies)


# 5. Casos Límite de Año de Publicación
def test_publication_year_out_of_range():
    """Años fuera del rango razonable (1800-2100) deben registrar anomalía."""
    record = {
        "numero_solicitud": "NC2026/000103",
        "titulo": "Procesador Fotónico",
        "anio_publicacion": 1500
    }
    result = validate_single_patent_record(record)
    assert any("fuera de rango" in anom for anom in result.anomalies)


# 6. Validación de Dataset Completo y Detección de Duplicados
def test_validate_dataset_with_duplicates():
    """El validador de conjunto debe identificar solicitudes repetidas."""
    dataset = [
        {"numero_solicitud": "NC2026/000200", "titulo": "Algoritmo A"},
        {"numero_solicitud": "NC2026/000201", "titulo": "Algoritmo B"},
        {"numero_solicitud": "NC2026/000200", "titulo": "Algoritmo A (Copia)"}
    ]
    summary = validate_patent_dataset(dataset)
    assert summary["total_records"] == 3
    assert len(summary["dataset_errors"]) == 1
    assert "NC2026/000200" in summary["dataset_errors"][0]