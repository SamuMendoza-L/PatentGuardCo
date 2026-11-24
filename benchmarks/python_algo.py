#!/usr/bin/env python3
"""
Benchmark del Algoritmo de Validación y Scoring de Patentes en Python.
Carga 20,000 registros en memoria y mide exclusivamente el tiempo de CPU/algorítmico
durante 20 iteraciones tras 2 de calentamiento.
"""

import json
import re
import statistics
import time
from typing import List, Dict, Any, Tuple, Optional

ISO_REGEX = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
DMY_REGEX = re.compile(r"^(\d{2})/(\d{2})/(\d{4})")


def parse_fecha(cadena: Any) -> Optional[Tuple[int, int, int]]:
    """Parsea fecha a tupla (año, mes, día) para comparación numérica instantánea."""
    if not cadena or not isinstance(cadena, str):
        return None
    c = cadena.split("T")[0].strip()
    m_iso = ISO_REGEX.match(c)
    if m_iso:
        return (int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
    m_dmy = DMY_REGEX.match(c)
    if m_dmy:
        return (int(m_dmy.group(3)), int(m_dmy.group(2)), int(m_dmy.group(1)))
    return None


def ejecutar_algoritmo_validacion(registros: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Ejecuta el algoritmo de validación determinista, detección de duplicados y scoring de riesgo.
    """
    total_validos = 0
    total_errores_obligatorios = 0
    total_advertencias_recomendados = 0
    total_anomalias_temporales = 0
    total_duplicados = 0
    
    riesgo_alto = 0
    riesgo_medio = 0
    riesgo_bajo = 0

    seen_ids = set()

    for rec in registros:
        errores = 0
        warnings = 0
        anomalias = 0
        score = 1.0

        # 1. Campos obligatorios
        num_sol = rec.get("numero_solicitud")
        if not num_sol or not isinstance(num_sol, str) or not num_sol.strip():
            errores += 1
            score += 2.0
            total_errores_obligatorios += 1
        else:
            num_clean = num_sol.strip()
            # Detección de duplicados mediante HashSet O(1)
            if num_clean in seen_ids:
                anomalias += 1
                score += 1.5
                total_duplicados += 1
            else:
                seen_ids.add(num_clean)

        titulo = rec.get("titulo")
        if not titulo or not isinstance(titulo, str) or not titulo.strip():
            errores += 1
            score += 2.0
            total_errores_obligatorios += 1

        # 2. Campos recomendados (Trazabilidad)
        solicitante = rec.get("solicitante")
        if not solicitante or not isinstance(solicitante, str) or not solicitante.strip():
            warnings += 1
            score += 0.5
            total_advertencias_recomendados += 1

        inventor = rec.get("inventor")
        if not inventor or not isinstance(inventor, str) or not inventor.strip():
            warnings += 1
            score += 0.5
            total_advertencias_recomendados += 1

        # 3. Coherencia temporal
        f_rad = parse_fecha(rec.get("fecha_radicacion"))
        f_pub = parse_fecha(rec.get("fecha_publicacion"))

        if f_rad and f_pub:
            if f_pub < f_rad:
                anomalias += 1
                score += 1.5
                total_anomalias_temporales += 1

        # Scoring de riesgo y clasificación
        score_final = min(5.0, score)
        if score_final >= 4.0:
            riesgo_alto += 1
        elif score_final >= 2.5:
            riesgo_medio += 1
        else:
            riesgo_bajo += 1

        if errores == 0:
            total_validos += 1

    return {
        "total_registros": len(registros),
        "total_validos": total_validos,
        "total_errores_obligatorios": total_errores_obligatorios,
        "total_advertencias_recomendados": total_advertencias_recomendados,
        "total_anomalias_temporales": total_anomalias_temporales,
        "total_duplicados": total_duplicados,
        "riesgo_alto": riesgo_alto,
        "riesgo_medio": riesgo_medio,
        "riesgo_bajo": riesgo_bajo,
    }


def main():
    ruta_dataset = "benchmarks/patents_sample.json"
    print(f"Cargando dataset {ruta_dataset} en memoria antes de cronometrar...")
    with open(ruta_dataset, "r", encoding="utf-8") as f:
        registros = json.load(f)
    print(f"Dataset cargado: {len(registros)} registros listos en RAM.")

    # 1. Calentamiento (2 iteraciones no cronometradas)
    print("Ejecutando 2 iteraciones de calentamiento (warmup)...")
    for _ in range(2):
        ejecutar_algoritmo_validacion(registros)

    # 2. Medición oficial (20 iteraciones cronometradas con time.perf_counter)
    print("Ejecutando 20 iteraciones oficiales de medición...")
    tiempos_ms = []
    res_final = None

    for i in range(20):
        t0 = time.perf_counter()
        res_final = ejecutar_algoritmo_validacion(registros)
        t_ms = (time.perf_counter() - t0) * 1000.0
        tiempos_ms.append(t_ms)

    t_promedio = statistics.mean(tiempos_ms)
    t_min = min(tiempos_ms)
    t_max = max(tiempos_ms)
    t_std = statistics.stdev(tiempos_ms)
    throughput = (len(registros) / (t_promedio / 1000.0))

    print("\n" + "=" * 65)
    print("  RESULTADOS OFICIALES BENCHMARK - PYTHON")
    print("=" * 65)
    print(f"• Dataset evaluado:          {len(registros)} registros")
    print(f"• Iteraciones cronometradas: 20")
    print(f"• Tiempo Promedio:           {t_promedio:.2f} ms")
    print(f"• Tiempo Mínimo:             {t_min:.2f} ms")
    print(f"• Tiempo Máximo:             {t_max:.2f} ms")
    print(f"• Desviación estándar:       {t_std:.2f} ms")
    print(f"• Throughput:                {throughput:,.0f} registros/seg")
    print("-" * 65)
    print("VERIFICACIÓN DE CONTEO Y CONSISTENCIA:")
    for k, v in res_final.items():
        print(f"  • {k}: {v}")
    print("=" * 65)


if __name__ == "__main__":
    main()
