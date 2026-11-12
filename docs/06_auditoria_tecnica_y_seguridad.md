# Auditoría técnica y de seguridad — PatentGuard CO

**Fecha de auditoría:** 12 de noviembre de 2026  
**Alcance:** código fuente de `app/`, pruebas de `tests/`, `.gitignore`, `.env.example` y documentación en `docs/`.  
**Método:** revisión estática del repositorio, revisión de la suite automatizada y ejecución local de `pytest -q`. No se realizaron pruebas de intrusión, llamadas a Gemini ni consultas contra servicios externos.

## Resumen ejecutivo

PatentGuard CO es una API FastAPI académica bien separada en capas: entrada HTTP, consulta de datos abiertos, validación determinista y análisis cualitativo opcional con Gemini. La revisión confirma prácticas positivas: contrato Pydantic, errores externos controlados para el consumidor, exclusión de secretos en Git y una suite de 24 pruebas que pasa localmente.

El producto es apropiado como demostración académica y prototipo controlado, pero **no está preparado para exponerse públicamente sin controles adicionales**. Los riesgos prioritarios son la ausencia de autenticación y limitación de tasa, la falta de un límite en la cantidad de solicitudes por petición, y la dependencia de llamadas externas que pueden degradar la disponibilidad. También debe gobernarse el envío de información de inventores y descripciones de disputas a un proveedor de IA.

| Área | Dictamen | Fundamento |
| --- | --- | --- |
| Calidad funcional | Aceptable para alcance académico | Rutas, validación, normalización y degradación controlada están implementadas y probadas. |
| Seguridad de secretos | Aceptable con mejora pendiente | `.env` y patrones de credenciales están ignorados; no se halló una clave real rastreada. Falta gestión centralizada de secretos para producción. |
| Resiliencia y rendimiento | Parcial | Hay `timeout`, código asíncrono para datos abiertos y prueba de 25 peticiones simuladas; faltan límites, reutilización de cliente, *rate limiting* y pruebas con dependencias reales/controladas. |
| Privacidad | Parcial | La API puede procesar nombres de inventores y descripciones; faltan política de retención, consentimiento y minimización explícita antes de transferir datos a Gemini. |
| Preparación para Internet | No recomendada aún | No hay autenticación, autorización, limitación de tasa, observabilidad ni configuración segura de despliegue documentada. |

## Evidencia revisada

- `app/main.py`: rutas `/`, `/health` y `/analizar-conflicto`; coordinación de datos abiertos, validación y Gemini.
- `app/schemas.py`: modelos Pydantic de entrada/salida y límites de longitud por campo.
- `app/client_datos_abiertos.py`: consulta Socrata con `httpx`, límite de 10 s, `$limit=1` y limpieza básica de comillas/caracteres de control.
- `app/validator.py`: validación de campos, tipos, fechas, año y duplicados.
- `app/gemini_service.py`: cliente Gemini, esquema esperado y mapeo de errores frecuentes.
- `tests/`: 24 pruebas unitarias, de API, seguridad y concurrencia con dependencias simuladas.
- `.gitignore` y `.env.example`: exclusión de `.env`, llaves/certificados y plantilla sin secreto real.

La ejecución local de la evidencia produjo **24 pruebas aprobadas**. Se conserva una advertencia de deprecación de `fastapi.testclient`/Starlette; no invalida los resultados, pero conviene eliminarla al actualizar la estrategia de pruebas.

## Auditoría de calidad del producto

### Interfaces REST y comportamiento observable

La interfaz es simple y coherente para el alcance: `GET /health` permite una comprobación básica y `POST /analizar-conflicto` concentra el caso de uso. FastAPI genera OpenAPI y `/docs`, y Pydantic responde con HTTP 422 ante cargas inválidas. La respuesta distingue registros encontrados, solicitudes no localizadas, inconsistencias, análisis IA y limitaciones; esa separación favorece trazabilidad y evita presentar la IA como prueba legal.

Hallazgos:

| Prioridad | Hallazgo | Evidencia / impacto | Recomendación |
| --- | --- | --- | --- |
| Alta | No hay autenticación ni autorización en la ruta de análisis. | Cualquier cliente con acceso de red podría consumir cuota de Gemini, consultar registros y enviar contenido al proveedor externo. | Exigir autenticación para el endpoint, aplicar roles mínimos y separar un modo demostración sin Gemini. |
| Alta | No existe límite máximo para `numeros_solicitud`. | Aunque cada identificador tiene máximo 100 caracteres, una lista muy grande provoca consultas secuenciales y una carga prolongada. | Definir `max_length` para la lista (por ejemplo, 10 o el valor definido por el caso de negocio) y devolver 422 al excederlo. |
| Media | Se devuelven `raw_data` y `registros_encontrados` como `Dict[str, Any]`. | El contrato de salida es flexible; cambios en la fuente pueden exponer columnas inesperadas o romper consumidores. | Modelar el registro público y la respuesta con Pydantic; excluir o filtrar `raw_data` según necesidad. |
| Media | El estado de resultado está modelado como `str` libre. | El contrato documenta valores, pero no impide otros estados. | Usar `Literal["success", "partial_success", "error"]` o un `Enum`. |
| Baja | `/health` solo indica que el proceso responde. | No diferencia disponibilidad de datos abiertos, Gemini o configuración. | Mantener *liveness* actual y añadir un *readiness check* protegido si se requiere operación productiva. |

La API emplea HTTP 200 cuando las dependencias externas fallan y reporta `partial_success`. Es una elección válida para un resultado parcial del caso de negocio; debe documentarse formalmente para que los clientes no confundan éxito de transporte con análisis completo.

### Modelo de datos Pydantic

`ConflictAnalysisRequest` impone al menos una solicitud, una descripción de 10 a 5.000 caracteres, identificadores de hasta 100 caracteres e inventores de hasta 200. Estos límites reducen cargas accidentales y están cubiertos por pruebas de seguridad. `ConflictAnalysisResponse` obliga a devolver las secciones principales.

Limitaciones observadas:

- No se limita el cardinal de `inventores_reclamantes` ni el de `numeros_solicitud`.
- No se normalizan explícitamente espacios ni se restringe el juego de caracteres de una solicitud; el uso de `strip()` ocurre al consultar, pero el valor original puede aparecer en la respuesta de no encontrados.
- La respuesta de Gemini se analiza como JSON, pero no se valida de nuevo contra `DisputeAnalysisSchema` antes de devolverla. El esquema se utiliza para solicitar una salida estructurada al proveedor, no como validación local final.
- `GEMINI_MODEL` y `DATOS_ABIERTOS_RESOURCE_URL` existen en `config.py`, pero el servicio Gemini y el cliente de datos abiertos usan valores codificados. Esto puede causar una configuración aparente que no tiene efecto.

### Complejidad algorítmica de `validator.py`

Para un registro, `validate_single_patent_record` realiza un número constante de lecturas, validaciones y hasta dos análisis de fecha. Su complejidad temporal es **O(1)** y su memoria adicional es **O(1)**, sin contar el tamaño de los textos de entrada.

Para `validate_patent_dataset`, el recorrido es único y los conjuntos `seen_solicitudes` y `duplicate_solicitudes` permiten detectar duplicados en tiempo amortizado constante por elemento. Por tanto, para `n` registros el coste es **O(n)** en tiempo y **O(n)** en memoria (evaluaciones y conjunto de solicitudes). Es una implementación eficiente para el tamaño previsto de una petición moderada. La salida de duplicados proviene de un `set`, por lo que su orden no es determinista; para informes reproducibles conviene ordenar la lista antes de construir el mensaje.

La noción de `is_valid` solo depende de errores de campos obligatorios. Advertencias y anomalías no lo vuelven falso; esta regla es coherente con la documentación, pero los consumidores deben entenderla para no interpretar un registro con anomalías como completamente confiable.

### Eficiencia de Python/FastAPI asíncrono

El cliente de datos abiertos usa `httpx.AsyncClient` y `await`, lo que evita bloquear el bucle de eventos durante la espera de red. Cada consulta define además un *timeout* de 10 segundos y limita el proveedor a una coincidencia, dos medidas positivas de estabilidad.

No obstante, la ruta procesa los identificadores en un `for` secuencial y construye un `AsyncClient` nuevo por cada solicitud. En el peor caso, el tiempo de espera se aproxima a la suma de los tiempos de cada consulta. La llamada `evaluar_disputa_con_gemini()` es síncrona dentro de una ruta `async`; si el SDK bloquea durante la red, puede bloquear el bucle de eventos del *worker*.

La prueba de rendimiento demuestra que 25 solicitudes concurrentes **con dependencias simuladas** conservan aislamiento y un promedio interno menor a 150 ms. No mide latencia de Internet, consumo de cuota, saturación de *workers* ni comportamiento bajo Gemini real; por ello no debe convertirse en un SLA de producción.

Mejoras priorizadas:

1. Limitar el tamaño de la lista y aplicar *rate limiting* en el borde de la aplicación.
2. Reutilizar un `httpx.AsyncClient` gestionado por el ciclo de vida de FastAPI.
3. Consultar solicitudes independientes con concurrencia acotada (`asyncio.gather` y un semáforo), preservando *timeouts*.
4. Usar el cliente asíncrono oficial de Gemini, si está disponible, o ejecutar la llamada bloqueante en un *threadpool* con límites; añadir tiempo máximo, reintentos con retroceso y disyuntor (*circuit breaker*).
5. Instrumentar latencia, errores por proveedor y saturación, sin registrar contenidos sensibles.

### Estabilidad y riesgos de despliegue

| Riesgo | Estado actual | Acción de despliegue recomendada |
| --- | --- | --- |
| Indisponibilidad de datos.gov.co | Controlado parcialmente mediante `timeout` y excepción propia; se devuelve resultado parcial. | Añadir reintentos acotados, métricas y aviso operativo. |
| Cuota/caída de Gemini | Se traduce a limitación sin exponer el detalle al cliente. | Presupuesto de cuota, *rate limit* por usuario, tiempo máximo y modo degradado documentado. |
| Denegación de servicio | Límites por texto, pero no por número de elementos; sin limitación de tasa. | Límite de cardinalidad, proxy inverso/WAF, cuotas y tamaño máximo de cuerpo. |
| Configuración | `.env.example` es seguro y `.env` está ignorado; hay parámetros declarados sin uso efectivo. | Secret manager del entorno, validación de configuración al arranque y eliminar/usar las variables inconsistentes. |
| Registros y observabilidad | Se evita enviar detalles al cliente, pero no hay política de logging ni correlación. | Logs estructurados, ID de solicitud, redacción de PII y retención definida. |
| Dependencias | Versiones fijadas, lo que favorece reproducibilidad. | Automatizar escaneo de vulnerabilidades, actualización controlada y SBOM. |
| Pruebas de producción | No hay integración real ni prueba de despliegue. | Pipeline CI, prueba contra entorno *staging* con secretos efímeros y prueba de carga autorizada. |

## Ingeniería inversa y seguridad

### Estimación realista de ingeniería inversa

La ingeniería inversa debe analizarse por superficie expuesta. Si el repositorio es público, Python se entrega como fuente y su lectura no requiere decompilación. Si solo se distribuye un contenedor o archivos `.pyc`, la decompilación y revisión de rutas sigue siendo factible para un analista competente. Si la API se publica sin autenticación, la documentación `/docs`, OpenAPI y las respuestas HTTP exponen directamente el contrato.

| Escenario | Tiempo estimado | Qué puede obtener un analista competente | Condición |
| --- | --- | --- | --- |
| API pública con `/docs` o `/openapi.json` expuestos | 15–60 minutos | Endpoints, esquemas, ejemplos, códigos de respuesta y flujo básico por pruebas no destructivas. | Sin autenticación y con documentación predeterminada. |
| API pública sin documentación, con respuestas predecibles | 2–8 horas | Descubrimiento razonable de rutas, parámetros y comportamiento por enumeración moderada. | Sin controles de tasa o monitoreo que limiten el sondeo. |
| Imagen/contenedor o paquete `.pyc` disponible | 1–2 días | Reconstrucción aproximada de módulos Python, lógica de validación, URLs y dependencias. | No incluye secretos que estén correctamente inyectados en tiempo de ejecución. |
| Comprensión completa de reglas, operación y proveedores | 3–10 días | Modelo de amenazas, límites operativos y comportamientos de error mediante análisis y pruebas autorizadas. | Depende del acceso a configuración, observabilidad y entorno. |

Estas cifras son estimaciones defensivas, no una invitación a probar sistemas ajenos. La ofuscación puede elevar el esfuerzo, pero no reemplaza autenticación, autorización, protección de secretos, límites de tasa ni monitoreo. La defensa principal debe asumir que el código y contrato pueden ser conocidos.

### Riesgos y controles de `GEMINI_API_KEY`

El repositorio no contiene una clave real según el escaneo de archivos rastreados; `.gitignore` excluye `.env`, `*.pem`, `*.key`, `*.crt` y `secrets/`, mientras que `.env.example` contiene un marcador. `gemini_service.py` lee la clave desde el entorno y la prueba verifica el caso de ausencia. Son controles correctos de base.

Persisten riesgos relevantes:

- Una clave filtrada por variables de CI, logs, capturas, historial de Git o repositorios clonados permitiría consumo no autorizado, agotamiento de cuota y posibles costes o acceso al contexto permitido por esa clave.
- El detalle de errores se oculta al cliente en `main.py`, pero el propio servicio Gemini construye excepciones con texto del proveedor. Sin disciplina de logs, ese detalle puede acabar en registros internos.
- La clave se lee directamente del entorno; no hay rotación, identidad de carga de trabajo, alcance mínimo ni auditoría de uso implementados en el código.

Controles recomendados: almacenar secretos en un gestor de secretos del proveedor de despliegue, inyectarlos solo en tiempo de ejecución, rotarlos y revocarlos ante sospecha, restringir la clave por proyecto/cuota cuando el proveedor lo permita, impedir que CI imprima variables sensibles y ejecutar escaneo de secretos previo a cada *push*. Nunca debe incluirse una clave en una incidencia, captura de pantalla, prompt o prueba.

### Datos personales, inventores y publicación pública

Los nombres de inventores pueden proceder de datos abiertos, y el usuario puede enviar nombres de reclamantes y descripciones de una disputa. Que un dato sea accesible públicamente no habilita automáticamente cualquier reutilización, combinación, difusión o envío a terceros. En particular, una captura o publicación en redes sociales puede contextualizar nombres con acusaciones de conflicto, afectar reputación y propagar información difícil de retirar. Un repositorio público también conserva historial y bifurcaciones.

Riesgos principales:

- Vincular nombres con alegaciones no verificadas de plagio, fraude o conflicto.
- Incluir en pruebas, documentación, issues, capturas o commits datos que no son estrictamente necesarios.
- Transferir descripciones y nombres a Gemini sin informar al usuario ni aplicar minimización.
- Publicar `raw_data` sin revisar las columnas que cambian en el proveedor.

Controles ya aplicados: el proyecto usa datos de prueba en la suite, evita declarar culpabilidad, incluye descargos de no vinculación legal y no rastrea una clave Gemini. Controles pendientes: aviso de privacidad, base jurídica/consentimiento aplicable, minimización o seudonimización de reclamantes antes de Gemini, política de retención/borrado, revisión humana antes de publicaciones y lista de campos permitidos para la respuesta pública.

## Plan de remediación

| Horizonte | Acción verificable | Riesgo que reduce |
| --- | --- | --- |
| Inmediato | Limitar `numeros_solicitud` e inventores; añadir prueba de límite de cardinalidad. | Consumo excesivo y denegación de servicio. |
| Inmediato | Implementar autenticación, cuota por identidad y *rate limiting* en proxy o aplicación. | Abuso público y consumo de Gemini. |
| Corto plazo | Validar localmente la respuesta Gemini con `DisputeAnalysisSchema`; tipar respuesta y filtrar `raw_data`. | Contrato inestable y exposición de columnas imprevistas. |
| Corto plazo | Reutilizar cliente HTTP, acotar concurrencia y aislar la llamada síncrona de Gemini. | Latencia, bloqueo de *worker* y estabilidad. |
| Corto plazo | Resolver variables de configuración no usadas y validar configuración al inicio. | Despliegues inconsistentes. |
| Medio plazo | Definir aviso de privacidad, minimización, retención y proceso de respuesta a incidentes de secretos. | Privacidad y exposición de datos. |
| Medio plazo | Añadir CI con pruebas, escaneo SCA/secretos, cobertura y pruebas de integración en *staging*. | Regresiones y vulnerabilidades de dependencias. |

## Conclusión

La base técnica demuestra buenas decisiones para una fase académica: separación de responsabilidades, validación determinista antes de IA, pruebas reproducibles y manejo no revelador de errores en la API. Para una exposición real debe tratarse como un prototipo: la apertura sin autenticación permitiría entender y abusar del servicio rápidamente, y el tratamiento de datos de inventores requiere gobierno explícito. La prioridad es cerrar la superficie de abuso y establecer controles operativos y de privacidad antes de cualquier despliegue público.
