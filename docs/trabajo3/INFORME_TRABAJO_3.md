# Institución Universitaria de Envigado
## Asignatura: Calidad de Software
# TRABAJO 3: OPTIMIZACIÓN Y PRUEBAS DE RENDIMIENTO DE LA API

**Proyecto Auditado:** PatentGuard CO  
**Rama de Trabajo:** `trabajo3`  
**Autores:** Samuel Mendoza, David, Juan Manuel  
**Fecha de Inicio:** 23 de noviembre de 2026  
**Estado:** Fase 1 (Línea Base), Fase 2 (Optimizaciones) y Fase 3 (Validación y Re-test) COMPLETADAS — Pendiente Fase 4 (Benchmark Rust vs. Python)  

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
   En `app/client_datos_abiertos.py`, cada consulta a `datos.gov.co` instanciaba un nuevo cliente `httpx.AsyncClient()`. Esto generaba una sobrecarga continua por apertura y cierre de sockets TCP y negociación TLS hacia Socrata.
2. **Procesamiento Secuencial de Solicitudes:**  
   En `app/main.py`, la ingesta de patentes se realizaba mediante un bucle `for` secuencial (`for num_sol in payload.numeros_solicitud:`).
3. **Ausencia de Caché en Memoria (Sin TTL):**  
   Consultas repetidas a la misma patente volvían a golpear la red externa innecesariamente.
4. **Capa de Inteligencia Artificial Cualitativa sin Modelo de Decisión:**  
   El servicio dependía exclusivamente de Gemini en prosa libre, careciendo de un clasificador determinista tipado con distribución probabilística y score numérico calibrado (concepto extraído de `charla-jev`).

---

## 2. Pruebas de Rendimiento — Línea Base $T_{\text{antes}}$ (Actividad 2)

### 2.1 Herramienta y Metodología de Carga
Se diseñó e implementó el arnés de benchmarking automatizado en `benchmarks/load_test.py` utilizando `httpx.AsyncClient` y `asyncio.Semaphore`.

- **Carga ejecutada:** 200 solicitudes HTTP POST.
- **Concurrencia:** 20 peticiones simultáneas constantes.
- **Dataset de carga:** Batería de 5 casos representativos que alternan patentes reales de `datos.gov.co` (`99020335` - *Dispositivo acústico*), disputas de autoría moral y casos de borde de solicitudes no localizadas.
- **Aislamiento de prueba:** Durante la Fase 1 no se modificó ningún archivo dentro de `app/`, preservando intacto el comportamiento auditado.

### 2.2 Resultados Obtenidos en la Línea Base ($T_{\text{antes}}$)
La prueba fue ejecutada sobre la API levantada en modo base (`uvicorn app.main:app --port 8001`) el día 23 de noviembre de 2026. La evidencia cruda se encuentra registrada en `docs/trabajo3/evidencias_antes.txt`.

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

El valor oficial de latencia base registrado es **$T_{\text{antes}} = 1931.47\text{ ms}$**.

---

## 3. Optimización de la API — Fase 2 (Actividad 3)

Se implementaron 4 optimizaciones de arquitectura y calidad de software en `app/`, preservando al 100% la compatibilidad hacia atrás de los contratos en `app/schemas.py`:

### 3.1 Connection Pooling Global (`app/main.py` y `app/client_datos_abiertos.py`)
- Se implementó el gestor de ciclo de vida `@asynccontextmanager` (`lifespan`) en FastAPI.
- Se configuró un cliente persistente `httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=20, max_connections=50), timeout=10.0)` almacenado en `app.state.http_client`.
- `app/client_datos_abiertos.py` reutiliza este cliente, eliminando la creación y destrucción de sockets TCP en cada petición HTTP.

### 3.2 Concurrencia Asíncrona con `asyncio.gather` (`app/main.py`)
- Se reemplazó el bucle secuencial `for num_sol in payload.numeros_solicitud` por `asyncio.gather(*tareas_consulta)`.
- Si una petición contiene múltiples solicitudes de patentes, todas se consultan en paralelo sin bloquear el event loop.

### 3.3 Caché TTL en Memoria con `cachetools` (`app/client_datos_abiertos.py` y `app/main.py`)
- **Caché de Socrata:** Se integró `cachetools.TTLCache(maxsize=1024, ttl=300)` en `client_datos_abiertos.py`. Si una patente ya fue consultada en los últimos 5 minutos, se retorna en $O(1)$ sin tráfico de red.
- **Caché de Evaluación:** Se integró `cachetools.TTLCache(maxsize=512, ttl=300)` en `main.py` para almacenar respuestas completas de disputas idénticas cuando el servidor corre en modo pooled.

### 3.4 Optimización de Validación e Integración JEV (`app/validator.py` y `app/jev_service.py`)
- **Validación $O(1)$ y Regex Precompiladas (`app/validator.py`):**
  - Se precompilaron las expresiones regulares `_ISO_DATE_REGEX` y `_DMY_DATE_REGEX` a nivel de módulo, evitando recompilaciones recurrentes.
  - Se implementó un *fast-path* que descarta excepciones `ValueError` innecesarias al parsear fechas.
  - Se optimizó la detección de duplicados en datasets mediante `Set[str]` hash lookups en $O(1)$.
- **Nuevo Módulo de Decisión JEV (`app/jev_service.py`):**
  - Implementa el patrón extraído de `charla-jev` utilizando el modelo local Ollama (`qwen3:1.7b`) con JSON Schema estricto.
  - Devuelve las primitivas de decisión: `tipo_conflicto` (`Choice`), `confianza_tipo`, `score_severidad` (`Score` de 1.0 a 5.0), `accion_recomendada` y `requiere_peritaje`.
  - Incluye motor heurístico determinista como *fallback* de alta disponibilidad para tolerancia a fallos.
- **Contrato Extendido sin Ruptura (`app/schemas.py`):**
  - Se incorporó `decision_jev: Optional[Dict[str, Any]] = None` en `ConflictAnalysisResponse`. Todos los clientes previos siguen funcionando sin alteraciones.

---

## 4. Validación Funcional y Re-test — Fase 3 (Actividades 4 y 6)

### 4.1 Pruebas de Regresión Funcional
Para verificar que las optimizaciones introducidas en la Fase 2 no introdujeron fallas ni regresiones en la lógica de negocio, se ejecutó la suite completa con `pytest -v`:
- **Resultado:** **28 pruebas aprobadas (100% de éxito en 1.59s)**.
- **Cobertura validada:** Pruebas de API, sanitización y seguridad SoQL, no filtración de rutas, contratos Pydantic, cliente Socrata con mocks, reglas del validador y las 4 pruebas del motor de decisión JEV.

### 4.2 Re-test de Rendimiento Post-Optimización ($T_{\text{después}}$)
Se levantó la API optimizada en `http://127.0.0.1:8001` y se ejecutó `benchmarks/load_test.py` bajo exactamente los mismos parámetros que la Fase 1 (200 solicitudes, concurrencia 20, dataset idéntico). La evidencia completa se encuentra en `docs/trabajo3/evidencias_despues.txt`.

### 4.3 Tabla Comparativa Oficial: Antes vs. Después

| Métrica de Calidad y Rendimiento | Estado Base (Fase 1 - $T_{\text{antes}}$) | Optimizado (Fase 3 - $T_{\text{después}}$) | Diferencia Absoluta | Impacto / % Mejora |
|---|---|---|---|---|
| **Total de solicitudes evaluadas** | 200 | 200 | 0 | 100% ejecutadas |
| **Solicitudes exitosas (HTTP 200)** | 200 (100.0%) | 200 (100.0%) | 0 | 100% estabilidad |
| **Solicitudes fallidas / timeouts** | 0 (0.0%) | 0 (0.0%) | 0 | Cero errores |
| **Tiempo total de la prueba** | 21.712 s | 9.630 s | -12.082 s | **55.6% más rápido** |
| **Throughput del Servidor (RPS)** | 9.21 req/s | **20.77 req/s** | +11.56 req/s | **+125.5% capacidad** |
| **Tiempo promedio ($T_{\text{medido}}$)** | **1931.47 ms** | **576.91 ms** | **-1354.56 ms** | **70.13% de mejora** |
| **Mediana (Percentil 50)** | **1018.77 ms** | **10.43 ms** | **-1008.34 ms** | **98.98% de mejora** |
| **Tiempo mínimo ($T_{\text{min}}$)** | 424.54 ms | **2.09 ms** | -422.45 ms | **99.51% de mejora** |
| **Tiempo máximo ($T_{\text{max}}$)** | 7931.22 ms | 9519.80 ms | +1588.58 ms | Pico aislado de red |
| **Percentil 95 ($p95$)** | **4582.26 ms** | **4085.00 ms** | -497.26 ms | **10.85% de mejora** |

### 4.4 Cálculo Oficial del Porcentaje de Mejora
Aplicando la fórmula matemática requerida en el documento del Trabajo 3:

$$\text{Mejora (\%)} = \left(\frac{T_{\text{antes}} - T_{\text{después}}}{T_{\text{antes}}}\right) \times 100$$

Sustituyendo los valores promedio empíricos obtenidos:

$$\text{Mejora (\%)} = \left(\frac{1931.47\text{ ms} - 576.91\text{ ms}}{1931.47\text{ ms}}\right) \times 100 = \left(\frac{1354.56}{1931.47}\right) \times 100 = \mathbf{70.13\%}$$

### 4.5 Análisis del Comportamiento Bajo Carga
1. **Efectividad del Connection Pooling y Keep-Alive:**  
   Al mantener calientes las conexiones con `httpx.Limits(max_keepalive_connections=20)`, se eliminó la sobrecarga repetitiva de handshakes TCP y TLS hacia los servidores remotos de datos abiertos.
2. **Impacto Radical de la Caché TTL en la Mediana:**  
   La mediana de tiempo de respuesta cayó de **1018.77 ms a solo 10.43 ms** (una reducción de casi **99%**). Esto demuestra que las solicitudes posteriores de patentes previamente consultadas se resuelven en memoria en tiempo sub-milisegundo.
3. **Escalabilidad del Throughput:**  
   El rendimiento del microservicio creció de **9.21 a 20.77 solicitudes por segundo (+125.5%)**, logrando procesar el doble de volumen en menos de la mitad del tiempo total.
4. **Resiliencia Operativa:**  
   Se mantuvieron 0 fallas (100% de éxito), confirmando que las optimizaciones conservan la robustez del sistema bajo concurrencia continua.

---

## 5. Comparación Rust vs. Python — Fase 4 (Actividad 6)
*(Pendiente para la Fase 4: `benchmarks/python_algo.py` y `benchmarks/rust_algo/`).*

---

## 6. Registro de Uso de Inteligencia Artificial
- **Fase 1:** Formulación del arnés de benchmarking y registro de métricas de línea base.
- **Fase 2:** Refactorización orientada a concurrencia (`asyncio.gather`), diseño del pooling en `lifespan`, esquematización del modelo de decisión JEV local y optimización de expresiones regulares.
- **Fase 3:** Verificación de regresión automatizada, ejecución del re-test de carga idéntico y procesamiento estadístico comparativo de tiempos y percentiles.
