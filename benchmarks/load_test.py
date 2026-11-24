#!/usr/bin/env python3
"""
Script de pruebas de carga y rendimiento para PatentGuard CO.
Diseñado para la medición de Línea Base (T_antes) y Validación Posterior (T_después)
según los lineamientos del Trabajo 3 de Calidad de Software.
"""

import argparse
import asyncio
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

import httpx

# Payloads de prueba representativos del dominio de patentes
BENCHMARK_PAYLOADS: List[Dict[str, Any]] = [
    {
        "numeros_solicitud": ["99020335"],
        "descripcion_conflicto": "Se solicita revisar la trazabilidad de autoría del dispositivo acústico publicado en el registro abierto.",
        "inventores_reclamantes": ["HENRY AZIMA", "JOERG PANZER"],
    },
    {
        "numeros_solicitud": ["99020335"],
        "descripcion_conflicto": "Disputa sobre derechos morales de desarrollo y software de transductores electroacústicos.",
        "inventores_reclamantes": ["Samuel Mendoza", "David Ospina"],
    },
    {
        "numeros_solicitud": ["99020335"],
        "descripcion_conflicto": "Conflicto de intereses: la entidad solicitante explota comercialmente la invención omitiendo a los inventores originales.",
        "inventores_reclamantes": ["Juan Manuel", "Samuel Mendoza"],
    },
    {
        "numeros_solicitud": ["NC2026/000123"],
        "descripcion_conflicto": "Registro hipotético no publicado en datos abiertos para evaluar el manejo de solicitudes no encontradas.",
        "inventores_reclamantes": ["Desarrollador Anónimo"],
    },
    {
        "numeros_solicitud": ["99020335", "NC2026/000456"],
        "descripcion_conflicto": "Comparativa múltiple de dos solicitudes para evaluar la detección de inconsistencias combinadas.",
        "inventores_reclamantes": ["HENRY AZIMA", "Auditor de Calidad"],
    },
]


async def _enviar_solicitud(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """Envía una única solicitud HTTP POST al endpoint controlando la concurrencia."""
    async with semaphore:
        inicio = time.perf_counter()
        status_code = 0
        error_msg = None
        try:
            response = await client.post(url, json=payload, timeout=30.0)
            status_code = response.status_code
            es_exitosa = 200 <= status_code < 300
            if not es_exitosa:
                error_msg = f"HTTP {status_code}"
        except httpx.TimeoutException:
            es_exitosa = False
            error_msg = "Timeout (>30s)"
        except httpx.RequestError as exc:
            es_exitosa = False
            error_msg = f"ConnectionError: {type(exc).__name__}"
        except Exception as exc:
            es_exitosa = False
            error_msg = f"UnexpectedError: {str(exc)}"

        duracion_ms = (time.perf_counter() - inicio) * 1000.0
        return {
            "duracion_ms": duracion_ms,
            "status_code": status_code,
            "es_exitosa": es_exitosa,
            "error_msg": error_msg,
        }


async def ejecutar_benchmark(
    url: str,
    total_solicitudes: int,
    concurrencia: int,
    label: str,
    archivo_salida: str,
) -> Dict[str, Any]:
    """Ejecuta la batería de pruebas de carga y genera el informe técnico."""
    semaphore = asyncio.Semaphore(concurrencia)
    print(f"\n{'='*75}")
    print(f"  BENCHMARK DE RENDIMIENTO: {label}")
    print(f"{'='*75}")
    print(f"• URL objetivo:          {url}")
    print(f"• Total de solicitudes:  {total_solicitudes}")
    print(f"• Concurrencia máxima:   {concurrencia} peticiones simultáneas")
    print(f"• Inicio de ejecución:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'-'*75}")

    t_inicio_total = time.perf_counter()

    async with httpx.AsyncClient() as client:
        # Preparamos las tareas distribuyendo los payloads cíclicamente
        tareas = [
            _enviar_solicitud(
                client=client,
                url=url,
                payload=BENCHMARK_PAYLOADS[i % len(BENCHMARK_PAYLOADS)],
                semaphore=semaphore,
            )
            for i in range(total_solicitudes)
        ]
        resultados = await asyncio.gather(*tareas)

    t_total_seg = time.perf_counter() - t_inicio_total

    # Cálculo estadístico de métricas
    duraciones = [r["duracion_ms"] for r in resultados]
    exitosas = sum(1 for r in resultados if r["es_exitosa"])
    fallidas = total_solicitudes - exitosas
    tasa_exito = (exitosas / total_solicitudes) * 100.0
    throughput_rps = total_solicitudes / t_total_seg if t_total_seg > 0 else 0.0

    duraciones_ordenadas = sorted(duraciones)
    t_min = min(duraciones)
    t_max = max(duraciones)
    t_promedio = statistics.mean(duraciones)
    t_mediana = statistics.median(duraciones)
    
    def _percentil(p: float) -> float:
        idx = int(len(duraciones_ordenadas) * p)
        return duraciones_ordenadas[min(idx, len(duraciones_ordenadas) - 1)]

    p90 = _percentil(0.90)
    p95 = _percentil(0.95)
    p99 = _percentil(0.99)
    desviacion_std = statistics.stdev(duraciones) if len(duraciones) > 1 else 0.0

    # Desglose de códigos y errores
    conteo_status: Dict[int, int] = {}
    errores_detalle: Dict[str, int] = {}
    for r in resultados:
        conteo_status[r["status_code"]] = conteo_status.get(r["status_code"], 0) + 1
        if r["error_msg"]:
            errores_detalle[r["error_msg"]] = errores_detalle.get(r["error_msg"], 0) + 1

    # Formateo del reporte
    lineas_reporte = [
        "=" * 75,
        f"  EVIDENCIA DE PRUEBAS DE CARGA Y RENDIMIENTO: {label}",
        "=" * 75,
        f"Fecha y hora:            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Plataforma:              {platform.system()} {platform.release()} ({platform.machine()})",
        f"Entorno Python:          {platform.python_version()} ({sys.executable})",
        f"Endpoint evaluado:       {url}",
        f"Parámetros de carga:     {total_solicitudes} solicitudes (Concurrencia: {concurrencia})",
        "-" * 75,
        "RESUMEN DE EJECUCIÓN (Métricas requeridas Trabajo 3):",
        f"  • Tiempo total de prueba:       {t_total_seg:.3f} s",
        f"  • Solicitudes ejecutadas:       {total_solicitudes}",
        f"  • Solicitudes exitosas (2xx):   {exitosas} ({tasa_exito:.1f}%)",
        f"  • Solicitudes fallidas:         {fallidas} ({100.0 - tasa_exito:.1f}%)",
        f"  • Throughput (RPS):             {throughput_rps:.2f} req/s",
        "-" * 75,
        "TIEMPOS DE RESPUESTA (Latencia por solicitud):",
        f"  • T_promedio (T_medido):        {t_promedio:.2f} ms",
        f"  • Tiempo mínimo:                {t_min:.2f} ms",
        f"  • Tiempo máximo:                {t_max:.2f} ms",
        f"  • Mediana (p50):                {t_mediana:.2f} ms",
        f"  • Percentil 90 (p90):           {p90:.2f} ms",
        f"  • Percentil 95 (p95):           {p95:.2f} ms",
        f"  • Percentil 99 (p99):           {p99:.2f} ms",
        f"  • Desviación estándar:          {desviacion_std:.2f} ms",
        "-" * 75,
        "DISTRIBUCIÓN DE CÓDIGOS HTTP:",
    ]
    for codigo, cantidad in sorted(conteo_status.items()):
        lineas_reporte.append(f"  • HTTP {codigo}: {cantidad} ({cantidad/total_solicitudes*100:.1f}%)")

    if errores_detalle:
        lineas_reporte.append("-" * 75)
        lineas_reporte.append("DETALLE DE ERRORES / FALLAS REGISTRADAS:")
        for err, cant in errores_detalle.items():
            lineas_reporte.append(f"  • {err}: {cant}")

    lineas_reporte.extend([
        "=" * 75,
        "CONCLUSIÓN DE ESTADO TÉCNICO:",
        f"  El valor de latencia base registrado T_antes es de {t_promedio:.2f} ms con una tasa",
        f"  de éxito de {tasa_exito:.1f}%. Este valor servirá como denominador oficial para",
        "  el cálculo del porcentaje de mejora en la Fase 3:",
        "      Mejora (%) = ((T_antes - T_después) / T_antes) * 100",
        "=" * 75,
    ])

    reporte_str = "\n".join(lineas_reporte) + "\n"
    print(reporte_str)

    if archivo_salida:
        os.makedirs(os.path.dirname(archivo_salida), exist_ok=True)
        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write(reporte_str)
        print(f" Evidencia guardada exitosamente en: {archivo_salida}\n")

    return {
        "t_promedio": t_promedio,
        "p95": p95,
        "exitosas": exitosas,
        "fallidas": fallidas,
        "throughput": throughput_rps,
    }


def main():
    parser = argparse.ArgumentParser(description="Prueba de carga y rendimiento para PatentGuard CO")
    parser.add_argument("--url", default="http://127.0.0.1:8001/analizar-conflicto", help="URL del endpoint")
    parser.add_argument("--total", type=int, default=200, help="Total de solicitudes a enviar")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrencia simultánea")
    parser.add_argument("--label", default="LÍNEA BASE (T_antes) - FASE 1", help="Etiqueta del benchmark")
    parser.add_argument("--output", default="docs/trabajo3/evidencias_antes.txt", help="Ruta del archivo de salida")
    args = parser.parse_args()

    asyncio.run(
        ejecutar_benchmark(
            url=args.url,
            total_solicitudes=args.total,
            concurrencia=args.concurrency,
            label=args.label,
            archivo_salida=args.output,
        )
    )


if __name__ == "__main__":
    main()
