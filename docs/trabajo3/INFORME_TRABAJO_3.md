# Institución Universitaria de Envigado
## Asignatura: Calidad de Software
# TRABAJO 3: OPTIMIZACIÓN Y PRUEBAS DE RENDIMIENTO DE LA API

**Proyecto Auditado:** PatentGuard CO  
**Rama de Trabajo:** `trabajo3`  
**Autores:** Samuel Mendoza, David, Juan Manuel  
**Fecha de Inicio de Fase 1:** 23 de noviembre de 2026  
**Estado:** Fase 1 completada (Línea base registrada) — Pendiente Fase 2 (Optimización)  

---

## 1. Diagnóstico y Medición Inicial (Actividad 1)

### 1.1 Funcionalidad de la API Seleccionada
Para el desarrollo del Trabajo 3 se retomó la API auditada en el Trabajo 2 y se seleccionó su endpoint crítico:

- **Endpoint:** `POST /analizar-conflicto` (definido en `app/main.py`)
- **Contrato de Entrada:** `ConflictAnalysisRequest` (`app/schemas.py`)
  - `numeros_solicitud`: Lista de identificadores de patentes a consultar en el portal nacional de datos abiertos (`datos.gov.co`).
  - `descripcion_conflicto`: Texto explicativo de la disputa de autoría moral frente a la titularidad económica.
  - `inventores_reclamantes`: Nombres de los desarrolladores o inventores afectados.

### 1.2 Justificación Técnica del Diagnóstico (Cuellos de Botella del Estado Base)
A partir de la auditoría técnica consolidada en el Trabajo 2 (`INFORME_AUDITORIA_FINAL.md`), se evidenciaron las siguientes ineficiencias de rendimiento y arquitectura en el estado base:

1. **Creación Efímera de Conexiones HTTP (Sin Connection Pooling):**  
   En `app/client_datos_abiertos.py`, cada consulta a `datos.gov.co` instancia un nuevo cliente `httpx.AsyncClient()`. Esto genera una sobrecarga continua por apertura y cierre de conexiones TCP y negociación de certificados TLS hacia el proveedor Socrata.
2. **Procesamiento Secuencial de Solicitudes:**  
   En `app/main.py`, la ingesta de patentes se realiza mediante un bucle `for` secuencial (`for num_sol in payload.numeros_solicitud:`). Si una petición contiene múltiples solicitudes, la latencia se acumula linealmente.
3. **Ausencia de Caché en Memoria (Sin TTL):**  
   Las patentes registradas en `datos.gov.co` son registros históricos públicos inmutables en el corto y mediano plazo. En el estado base, consultas repetidas a la misma patente vuelven a golpear la red externa innecesariamente.
4. **Capa de Inteligencia Artificial Cualitativa sin Modelo de Decisión:**  
   El servicio actual dependía exclusivamente de la generación de texto libre con Gemini, careciendo de un clasificador determinista tipado con distribución probabilística y score de severidad numérico calibrado (concepto extraído de `charla-jev`).

### 1.3 Variables e Indicadores a Medir
De acuerdo con la rúbrica oficial del Trabajo 3, se definieron los siguientes indicadores cuantitativos:
- **$T_{\text{antes}}$:** Tiempo promedio de respuesta por solicitud en el estado base (en milisegundos).
- **Latencias de Distribución:** Tiempo mínimo, tiempo máximo, mediana (p50) y percentil 95 (p95).
- **Volumen de Solicitudes:** Solicitudes totales ejecutadas, exitosas (HTTP 2xx) y fallidas (HTTP 4xx/5xx o timeouts).
- **Throughput:** Peticiones procesadas por segundo (req/s).
- **Tasa de Error:** Porcentaje de fallas observadas bajo carga concurrente.

---

## 2. Pruebas de Rendimiento — Línea Base $T_{\text{antes}}$ (Actividad 2)

### 2.1 Herramienta y Metodología de Carga
Se diseñó e implementó el arnés de benchmarking automatizado en `benchmarks/load_test.py` utilizando `httpx.AsyncClient` y `asyncio.Semaphore`.

- **Carga ejecutada:** 200 solicitudes HTTP POST.
- **Concurrencia:** 20 peticiones simultáneas constantes.
- **Dataset de carga:** Batería de 5 casos representativos que alternan patentes reales de `datos.gov.co` (`99020335` - *Dispositivo acústico*), disputas de autoría moral y casos de borde de solicitudes no localizadas.
- **Aislamiento de prueba:** Durante esta Fase 1 **no se modificó ningún archivo dentro de `app/`**, preservando intacto el comportamiento auditado en el Trabajo 2.

### 2.2 Resultados Obtenidos en la Línea Base ($T_{\text{antes}}$)
La prueba fue ejecutada sobre la API levantada en modo base (`uvicorn app.main:app --port 8001`) el día 23 de noviembre de 2026. La evidencia completa y cruda se encuentra registrada en `docs/trabajo3/evidencias_antes.txt`.

| Métrica de Rendimiento | Valor Registrado (Estado Base - Línea Base) |
|---|---|
| **Total de solicitudes ejecutadas** | 200 |
| **Solicitudes exitosas (HTTP 200)** | 200 (100.0%) |
| **Solicitudes fallidas** | 0 (0.0%) |
| **Tiempo total de la prueba** | 21.712 segundos |
| **Throughput promedio** | **9.21 req/s** |
| **$T_{\text{promedio}}$ ($T_{\text{antes}}$ oficial)** | **1931.47 ms** (~1.93 s) |
| **Tiempo mínimo ($T_{\text{min}}$)** | 424.54 ms |
| **Tiempo máximo ($T_{\text{max}}$)** | 7931.22 ms (~7.93 s) |
| **Mediana (Percentil 50)** | 1018.77 ms |
| **Percentil 90 (p90)** | 4378.06 ms |
| **Percentil 95 (p95)** | **4582.26 ms** |
| **Percentil 99 (p99)** | 6706.90 ms |
| **Desviación estándar** | 1644.60 ms |

### 2.3 Análisis de Resultados de la Línea Base
El valor base **$T_{\text{antes}} = 1931.47\text{ ms}$** evidencia de manera empírica el cuello de botella pronosticado:
- El 95% de las solicitudes requirió hasta **4.58 segundos** para completarse bajo una concurrencia moderada de 20 hilos.
- La dispersión (desviación estándar de 1644 ms y pico máximo de 7.93 segundos) confirma la degradación sufrida al negociar handshakes TLS individuales contra Socrata sin reutilización de conexiones ni caché.
- Este valor de **$1931.47\text{ ms}$** se fija como el **denominador oficial** para calcular el porcentaje de mejora en la Fase 3.

---

## 3. Plan de Optimización — Fase 2 (Actividad 3)

Para la siguiente fase, se aplicarán las siguientes optimizaciones de ingeniería de software en `app/`:

1. **Connection Pooling Global:** Reutilización de una única instancia de `httpx.AsyncClient` acoplada al ciclo de vida (`lifespan`) de FastAPI en `app/main.py` e inyectada en `app/client_datos_abiertos.py`.
2. **Concurrencia con `asyncio.gather`:** Conversión del bucle secuencial de ingesta de patentes en consultas paralelas no bloqueantes.
3. **Caché TTL en Memoria (`cachetools`):** Almacenamiento temporal de registros de patentes públicas y de evaluaciones para eliminar el 100% de la latencia de red en consultas repetidas.
4. **Integración del Modelo de Decisión Local JEV (`app/jev_service.py`):** Incorporación del patrón de decisión de `charla-jev` ejecutado sobre el LLM local Ollama (`qwen3:1.7b`) con JSON Schema, asegurando un clasificador de severidad tipado, costo $0 y soporte offline.

---

## 4. Validación y Re-test — Fase 3 (Actividad 4 y 6)
*(Se completará al finalizar la implementación de las optimizaciones en la Fase 2).*

- **Fórmula de Evaluación de Rendimiento:**
  $$\text{Mejora (\%)} = \left(\frac{T_{\text{antes}} - T_{\text{después}}}{T_{\text{antes}}}\right) \times 100$$
- **Pruebas de Regresión:** Verificación de que la suite de `pytest` (24 pruebas) continúe aprobando al 100%.

---

## 5. Comparación Rust vs. Python — Fase 4 (Actividad 6)
*(Se completará en la Fase 4 mediante la implementación del algoritmo en `benchmarks/python_algo.py` y `benchmarks/rust_algo/`).*

- Algoritmo seleccionado: **Validación determinista de integridad de registros y detección de duplicados** (`validate_patent_dataset` de `app/validator.py`).
- Métrica: Tiempo de desarrollo, tiempo de compilación (Rust) y tiempo promedio de ejecución sobre `patents_sample.json`.

---

## 6. Registro de Uso de Inteligencia Artificial
- **Fase 1:** Se utilizó asistencia de IA como apoyo técnico para la formulación del arnés de benchmarking concurrente (`benchmarks/load_test.py`) y la extracción estructurada de métricas estadísticas (p90, p95, p99, throughput), manteniendo la integridad metodológica de no intervenir el código fuente de la API durante la medición de la línea base.
