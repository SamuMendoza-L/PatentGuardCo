#!/usr/bin/env python3
"""
Generador de dataset de prueba para benchmarking Python vs. Rust.
Produce 20,000 registros de patentes con casos válidos y anomalías controladas.
"""

import json
import random
import os

random.seed(42)

TITULOS_BASE = [
    "SISTEMA DE TRAZABILIDAD Y REGISTRO CRIPTOGRÁFICO",
    "DISPOSITIVO ELECTROACÚSTICO CON TRANSDUCTOR DE ALTA FIDELIDAD",
    "MÉTODO DE ENCRIPTACIÓN PARA COMUNICACIONES DISTRIBUIDAS",
    "SENSOR FOTÓNICO DE FIBRA ÓPTICA PARA MONITORIZACIÓN TÉRMICA",
    "APARATO DE FILTRADO MOLECULAR MEDIANTE MEMBRANAS NANOESTRUCTURADAS",
    "SISTEMA DE SEGURIDAD BIOMÉTRICA CON IDENTIFICACIÓN MULTIMODAL",
    "PROCESADOR NEUROMÓRFICO DE BAJO CONSUMO DE ENERGÍA",
    "MECANISMO DE PROPULSIÓN ELECTROMAGNÉTICA PARA MICROSATÉLITES",
    "COMPOSICIÓN POLIMÉRICA BIODEGRADABLE CON RESISTENCIA MEJORADA",
    "SISTEMA DE DETECCIÓN Y CLASIFICACIÓN DE SEÑALES RADAR"
]

SOLICITANTES = [
    "Universidad Tecnológica Nacional",
    "Instituto de Investigaciones Avanzadas S.A.S.",
    "Corporación para el Desarrollo Biotecnológico",
    "Industrias Electrónicas del Caribe Ltda.",
    "Laboratorios Farmacéuticos Andinos",
    "Fundación para la Innovación Abierta"
]

INVENTORES = [
    "Samuel Mendoza; Andrés Felipe",
    "David Ospina; Juan Manuel",
    "HENRY AZIMA; JOERG PANZER",
    "Elena Restrepo; Carlos Botero",
    "Mariana Gómez; Alejandro Vélez",
    "Gabriel Valencia; Sofía Arango"
]

ESTADOS = ["Publicada", "En trámite", "Concedida", "Abandonada"]


def generar_patentes(total: int = 20000, ruta_salida: str = "benchmarks/patents_sample.json"):
    registros = []
    
    # Pool de números de solicitud (con ~500 duplicados intencionales para probar colisiones)
    total_unicos = total - 500
    pool_solicitudes = [f"NC2026/{i:06d}" for i in range(1, total_unicos + 1)]
    # Añadimos 500 solicitudes repetidas seleccionadas del pool
    solicitudes = pool_solicitudes + random.choices(pool_solicitudes[:2000], k=500)
    random.shuffle(solicitudes)

    for i, num_sol in enumerate(solicitudes):
        es_invalida = (i % 50 == 0)      # 2% sin título (campo obligatorio ausente)
        falta_inventor = (i % 7 == 0)   # ~14% sin inventor (advertencia recomendada)
        falta_solicitante = (i % 15 == 0) # ~6% sin solicitante (advertencia recomendada)
        anomalia_fecha = (i % 80 == 0)  # ~1.2% fecha publicación anterior a radicación
        formato_dmy = (i % 5 == 0)      # ~20% formato DD/MM/AAAA

        # Título
        titulo = "" if es_invalida else random.choice(TITULOS_BASE)

        # Solicitante e inventor
        solicitante = "" if falta_solicitante else random.choice(SOLICITANTES)
        inventor = None if falta_inventor else random.choice(INVENTORES)

        # Fechas
        anio_rad = random.randint(2018, 2024)
        mes_rad = random.randint(1, 12)
        dia_rad = random.randint(1, 28)

        if anomalia_fecha:
            anio_pub = anio_rad - 1  # Inconsistencia temporal intencional
        else:
            anio_pub = anio_rad + random.randint(0, 2)
        mes_pub = random.randint(1, 12)
        dia_pub = random.randint(1, 28)

        if formato_dmy:
            fecha_rad = f"{dia_rad:02d}/{mes_rad:02d}/{anio_rad}"
            fecha_pub = f"{dia_pub:02d}/{mes_pub:02d}/{anio_pub}"
        else:
            fecha_rad = f"{anio_rad}-{mes_rad:02d}-{dia_rad:02d}"
            fecha_pub = f"{anio_pub}-{mes_pub:02d}-{dia_pub:02d}"

        registros.append({
            "numero_solicitud": num_sol,
            "titulo": titulo,
            "solicitante": solicitante,
            "inventor": inventor,
            "fecha_radicacion": fecha_rad,
            "fecha_publicacion": fecha_pub,
            "estado": random.choice(ESTADOS),
            "resumen": f"Descripción de invención técnica para la solicitud {num_sol}."
        })

    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)

    tamano_mb = os.path.getsize(ruta_salida) / (1024 * 1024)
    print(f"Dataset generado exitosamente: {total} registros en {ruta_salida} ({tamano_mb:.2f} MB)")


if __name__ == "__main__":
    generar_patentes(20000)
