use serde::Deserialize;
use std::collections::HashSet;
use std::fs::File;
use std::io::BufReader;
use std::time::Instant;

#[derive(Debug, Deserialize)]
struct PatentRecord {
    numero_solicitud: Option<String>,
    titulo: Option<String>,
    solicitante: Option<String>,
    inventor: Option<String>,
    fecha_radicacion: Option<String>,
    fecha_publicacion: Option<String>,
    estado: Option<String>,
    resumen: Option<String>,
}

#[derive(Debug, Default, PartialEq, Eq)]
struct MetricSummary {
    total_registros: usize,
    total_validos: usize,
    total_errores_obligatorios: usize,
    total_advertencias_recomendados: usize,
    total_anomalias_temporales: usize,
    total_duplicados: usize,
    riesgo_alto: usize,
    riesgo_medio: usize,
    riesgo_bajo: usize,
}

#[inline(always)]
fn parse_fecha(cadena: Option<&str>) -> Option<(u16, u8, u8)> {
    let raw = cadena?.split('T').next()?.trim();
    let bytes = raw.as_bytes();

    if bytes.len() >= 10 {
        // Formato ISO: YYYY-MM-DD
        if bytes[4] == b'-' && bytes[7] == b'-' {
            let y = raw[0..4].parse::<u16>().ok()?;
            let m = raw[5..7].parse::<u8>().ok()?;
            let d = raw[8..10].parse::<u8>().ok()?;
            return Some((y, m, d));
        }
        // Formato DMY: DD/MM/YYYY
        if bytes[2] == b'/' && bytes[5] == b'/' {
            let d = raw[0..2].parse::<u8>().ok()?;
            let m = raw[3..5].parse::<u8>().ok()?;
            let y = raw[6..10].parse::<u16>().ok()?;
            return Some((y, m, d));
        }
    }
    None
}

fn ejecutar_algoritmo(registros: &[PatentRecord]) -> MetricSummary {
    let mut resumen = MetricSummary {
        total_registros: registros.len(),
        ..Default::default()
    };

    let mut seen_ids: HashSet<&str> = HashSet::with_capacity(registros.len());

    for rec in registros {
        let mut errores = 0;
        let mut _warnings = 0;
        let mut _anomalias = 0;
        let mut score: f64 = 1.0;

        // 1. Campos obligatorios
        match &rec.numero_solicitud {
            Some(s) if !s.trim().is_empty() => {
                let num_clean = s.trim();
                // Detección de duplicados mediante HashSet O(1)
                if !seen_ids.insert(num_clean) {
                    _anomalias += 1;
                    score += 1.5;
                    resumen.total_duplicados += 1;
                }
            }
            _ => {
                errores += 1;
                score += 2.0;
                resumen.total_errores_obligatorios += 1;
            }
        }

        match &rec.titulo {
            Some(s) if !s.trim().is_empty() => {}
            _ => {
                errores += 1;
                score += 2.0;
                resumen.total_errores_obligatorios += 1;
            }
        }

        // 2. Campos recomendados (Trazabilidad)
        match &rec.solicitante {
            Some(s) if !s.trim().is_empty() => {}
            _ => {
                _warnings += 1;
                score += 0.5;
                resumen.total_advertencias_recomendados += 1;
            }
        }

        match &rec.inventor {
            Some(s) if !s.trim().is_empty() => {}
            _ => {
                _warnings += 1;
                score += 0.5;
                resumen.total_advertencias_recomendados += 1;
            }
        }

        // 3. Coherencia temporal
        let f_rad = parse_fecha(rec.fecha_radicacion.as_deref());
        let f_pub = parse_fecha(rec.fecha_publicacion.as_deref());

        if let (Some(rad), Some(publ)) = (f_rad, f_pub) {
            if publ < rad {
                _anomalias += 1;
                score += 1.5;
                resumen.total_anomalias_temporales += 1;
            }
        }

        // Scoring de riesgo y clasificación
        let score_final = score.min(5.0);
        if score_final >= 4.0 {
            resumen.riesgo_alto += 1;
        } else if score_final >= 2.5 {
            resumen.riesgo_medio += 1;
        } else {
            resumen.riesgo_bajo += 1;
        }

        if errores == 0 {
            resumen.total_validos += 1;
        }
    }

    resumen
}

fn main() {
    let ruta_dataset = "../patents_sample.json";
    println!("Cargando dataset {} en memoria antes de cronometrar...", ruta_dataset);

    let file = File::open(ruta_dataset)
        .or_else(|_| File::open("benchmarks/patents_sample.json"))
        .expect("No fue posible abrir patents_sample.json");

    let reader = BufReader::new(file);
    let registros: Vec<PatentRecord> = serde_json::from_reader(reader)
        .expect("Error al deserializar JSON de patentes");

    println!("Dataset cargado: {} registros listos en RAM.", registros.len());

    // 1. Calentamiento (2 iteraciones no cronometradas)
    println!("Ejecutando 2 iteraciones de calentamiento (warmup)...");
    for _ in 0..2 {
        let _ = ejecutar_algoritmo(&registros);
    }

    // 2. Medición oficial (20 iteraciones cronometradas)
    println!("Ejecutando 20 iteraciones oficiales de medición...");
    let mut tiempos_ms = Vec::with_capacity(20);
    let mut res_final = MetricSummary::default();

    for _ in 0..20 {
        let t0 = Instant::now();
        res_final = ejecutar_algoritmo(&registros);
        let t_ms = t0.elapsed().as_secs_f64() * 1000.0;
        tiempos_ms.push(t_ms);
    }

    let t_promedio = tiempos_ms.iter().sum::<f64>() / (tiempos_ms.len() as f64);
    let t_min = tiempos_ms.iter().cloned().fold(f64::INFINITY, f64::min);
    let t_max = tiempos_ms.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let throughput = (registros.len() as f64) / (t_promedio / 1000.0);

    println!("\n=================================================================");
    println!("  RESULTADOS OFICIALES BENCHMARK - RUST (RELEASE)");
    println!("=================================================================");
    println!("• Dataset evaluado:          {} registros", registros.len());
    println!("• Iteraciones cronometradas: 20");
    println!("• Tiempo Promedio:           {:.2} ms", t_promedio);
    println!("• Tiempo Mínimo:             {:.2} ms", t_min);
    println!("• Tiempo Máximo:             {:.2} ms", t_max);
    println!("• Throughput:                {:.0} registros/seg", throughput);
    println!("-----------------------------------------------------------------");
    println!("VERIFICACIÓN DE CONTEO Y CONSISTENCIA:");
    println!("  • total_registros: {}", res_final.total_registros);
    println!("  • total_validos: {}", res_final.total_validos);
    println!("  • total_errores_obligatorios: {}", res_final.total_errores_obligatorios);
    println!("  • total_advertencias_recomendados: {}", res_final.total_advertencias_recomendados);
    println!("  • total_anomalias_temporales: {}", res_final.total_anomalias_temporales);
    println!("  • total_duplicados: {}", res_final.total_duplicados);
    println!("  • riesgo_alto: {}", res_final.riesgo_alto);
    println!("  • riesgo_medio: {}", res_final.riesgo_medio);
    println!("  • riesgo_bajo: {}", res_final.riesgo_bajo);
    println!("=================================================================");
}
