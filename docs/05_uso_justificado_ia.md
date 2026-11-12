# Uso justificado de IA y pruebas de calidad de software

## Propósito

PatentGuard CO usa Gemini como apoyo para elaborar una evaluación cualitativa de un conflicto de autoría. La IA no determina la titularidad ni emite un dictamen jurídico: recibe los datos recuperados, las inconsistencias detectadas por reglas deterministas y los inventores reclamantes, y produce una respuesta JSON orientativa con descargo legal.

La calidad del sistema no depende exclusivamente de la IA. Primero se aplican validaciones reproducibles sobre los datos; luego Gemini complementa la interpretación ética. Esta separación permite probar el comportamiento técnico sin usar una clave real ni realizar llamadas externas.

## Estrategia de pruebas aplicada

Las pruebas se implementaron con **pytest** y están ubicadas en la carpeta `tests/`. La suite contiene **18 pruebas automatizadas aprobadas**. Se utilizan *mocks* para reemplazar `datos.gov.co` y Gemini durante la ejecución; por eso las pruebas son repetibles, rápidas y no consumen cuota de la API.

```bash
.venv/bin/pytest -v --tb=short
```

### Clasificación general

| Tipo de prueba | Aplicación en el proyecto | Alcance |
| --- | --- | --- |
| **Prueba unitaria** | Validador, cliente de datos abiertos y servicio Gemini. | Verifica una función o módulo de forma aislada. |
| **Prueba de componente/API** | Rutas `/health` y `/analizar-conflicto`. | Verifica la integración interna de FastAPI, esquemas y servicios simulados. |
| **Prueba de caja negra** | Casos válidos, entradas inválidas, errores HTTP, *timeout* y JSON inválido. | Valida entradas y salidas sin depender de la implementación interna. |
| **Prueba negativa y de robustez** | Ausencia de campos, tipos erróneos, cuota Gemini, datos no encontrados y respuesta malformada. | Confirma que el sistema controle fallos sin detenerse. |
| **Prueba de integridad y unicidad de datos** | Detección de solicitudes duplicadas. | Revisa que un mismo número de solicitud no aparezca repetido en un conjunto de registros. |

> No se implementó una prueba de sistema completa contra los servicios reales. Las integraciones externas se simulan deliberadamente para mantener las pruebas deterministas. La consulta manual de la solicitud pública `99020335` sirve como evidencia complementaria de integración con datos abiertos.

## Inventario de pruebas

### 1. Pruebas unitarias del validador

**Ubicación:** `tests/test_validator.py`  
**Componente probado:** `app/validator.py`  
**Técnica:** prueba unitaria, caja negra, partición de equivalencia, valores límite e integridad de datos.

| Nombre técnico de la prueba | Cómo se realiza | Qué valida | Resultado esperado |
| --- | --- | --- | --- |
| `test_valid_patent_record` | Envía un registro completo y coherente. | Camino válido o partición de equivalencia válida. | Registro válido, sin errores, advertencias ni anomalías. |
| `test_missing_mandatory_fields` | Omite `numero_solicitud` y `titulo`. | Validación de campos obligatorios. | Registro inválido y dos errores de integridad. |
| `test_missing_recommended_fields` | Envía `solicitante` vacío e `inventor` nulo. | Validación de trazabilidad y caso negativo. | Registro técnicamente válido, pero con dos advertencias. |
| `test_unexpected_data_types_and_date_anomalies` | Usa un solicitante numérico, fechas incoherentes y año de tipo incorrecto. | Robustez, validación de tipos y consistencia temporal. | Anomalías por tipo, fecha de publicación anterior y año inválido. |
| `test_publication_year_out_of_range` | Envía el año `1500`. | Prueba de valor límite de dominio. | Anomalía por año fuera del rango razonable `1800-2100`. |
| `test_validate_dataset_with_duplicates` | Envía tres registros, dos con la misma solicitud. | Integridad referencial y **unicidad** del identificador. | Error de conjunto que reporta la solicitud duplicada. |

### 2. Pruebas unitarias del cliente de datos abiertos

**Ubicación:** `tests/test_client_datos_abiertos.py`  
**Componente probado:** `app/client_datos_abiertos.py`  
**Técnica:** prueba unitaria asíncrona, simulación de dependencia externa mediante `unittest.mock`.

| Nombre técnico de la prueba | Cómo se realiza | Qué valida | Resultado esperado |
| --- | --- | --- | --- |
| `test_consultar_patente_exitoso` | Simula una respuesta HTTP 200 con un registro. | Consulta, normalización y mapeo de datos. | Diccionario estructurado con solicitud, solicitante e inventor. |
| `test_consultar_patente_no_encontrada` | Simula una lista JSON vacía. | Caso de búsqueda sin resultados. | Retorno `None`, sin excepción. |
| `test_manejo_error_http` | Simula `HTTPStatusError` con código 500. | Manejo controlado de error del proveedor. | Excepción `DatosAbiertosAPIError` con el código HTTP. |
| `test_manejo_timeout` | Simula `TimeoutException`. | Resiliencia ante demora o indisponibilidad de red. | Excepción controlada con mensaje de tiempo agotado. |
| `test_manejo_json_invalido` | Simula un fallo al convertir la respuesta a JSON. | Validación de formato de respuesta externa. | Excepción controlada que informa JSON inválido. |

### 3. Pruebas unitarias del servicio Gemini

**Ubicación:** `tests/test_gemini_service.py`  
**Componente probado:** `app/gemini_service.py`  
**Técnica:** prueba unitaria con *mock*, validación de contrato JSON y manejo de errores de servicio.

| Nombre técnico de la prueba | Cómo se realiza | Qué valida | Resultado esperado |
| --- | --- | --- | --- |
| `test_evaluar_disputa_exitoso` | Inyecta un cliente Gemini simulado que devuelve JSON estructurado. | Procesamiento de respuesta, estructura ética y llamada al modelo. | Diccionario con resumen, hechos, análisis ético y recomendaciones. |
| `test_error_falta_api_key` | Elimina temporalmente `GEMINI_API_KEY` del entorno. | Configuración obligatoria y seguridad de credenciales. | Excepción `GeminiServiceError` que indica la variable faltante. |
| `test_manejo_error_limite_cuota` | Simula `APIError` HTTP 429 con `RESOURCE_EXHAUSTED`. | Manejo de límite de cuota o *rate limit*. | Excepción controlada: "Límite de cuota excedido". |
| `test_manejo_respuesta_json_invalida` | Simula texto plano en vez de JSON. | Contrato de salida estructurada de la IA. | Excepción controlada de error al parsear JSON. |

### 4. Pruebas de componente y API

**Ubicación:** `tests/test_api.py`  
**Componente probado:** `app/main.py` y las rutas FastAPI.  
**Técnica:** prueba de componente/API en memoria con `FastAPI TestClient`, `AsyncMock` y *mocks* de Gemini.

| Nombre técnico de la prueba | Cómo se realiza | Qué valida | Resultado esperado |
| --- | --- | --- | --- |
| `test_health_check_endpoint` | Solicita `GET /health`. | Disponibilidad básica de la API. | HTTP 200 y JSON con `status: "ok"`. |
| `test_analizar_conflicto_exitoso` | Simula un registro de patente, una advertencia de inventor ausente y una respuesta Gemini asociada a Samuel Mendoza y Andrés Felipe. | Flujo integrado: entrada, consulta, validación, análisis IA y respuesta JSON. | HTTP 200, estado `success`, un registro encontrado y análisis ético presente. |
| `test_analizar_conflicto_payload_invalido` | Envía lista de solicitudes vacía y descripción muy corta. | Validación de contrato mediante Pydantic. | HTTP 422 `Unprocessable Entity`. |

## Resultado de la ejecución

### Remediación y hardening — Fase 1

| Cambio aplicado | Archivo | Justificación de calidad |
| --- | --- | --- |
| Migración de `min_items` y `example` a `min_length` y `json_schema_extra={"examples": [...]}`. | `app/schemas.py` | Elimina las advertencias de atributos deprecados de Pydantic V1 y mantiene las mismas reglas de validación y ejemplos del contrato OpenAPI. |
| Inclusión de `solicitudes_no_encontradas` en la respuesta y de `tiempo_procesamiento_ms` en las métricas de procesamiento. | `app/schemas.py`, `app/main.py` | Expone de forma trazable las consultas sin coincidencia y permite observar el tiempo total del endpoint, sin modificar su flujo de negocio. |
| Eliminación de comillas simples y caracteres de control antes de construir `$where`. | `app/client_datos_abiertos.py` | Reduce el riesgo de inyección o de consultas SoQL malformadas, manteniendo la consulta remota limitada a una coincidencia. |
| Sustitución de `google-generativeai` por `google-genai` y fijación de versiones usadas por el proyecto. | `requirements.txt` | Alinea las dependencias reproducibles con el SDK que importa `app/gemini_service.py` y con el entorno validado. |

La ejecución posterior a la remediación se realiza con:

```text
pytest -v
```

Resultado verificado: `18 passed, 1 warning`. No se emitieron advertencias de Pydantic. La única advertencia restante procede de `fastapi.testclient`/Starlette e informa una transición interna hacia `httpx2`; no corresponde a la aplicación ni a los esquemas Pydantic remediados.

## Conclusión sobre el uso de Gemini

Gemini está justificado como una capa de apoyo cualitativo para organizar hallazgos, explicar limitaciones y formular recomendaciones relacionadas con la tensión entre autoría y lucro. La decisión técnica relevante no se delega a la IA: los campos obligatorios, la unicidad de las solicitudes, los tipos de datos y las fechas se evalúan mediante reglas de código comprobables.

Por esta razón, un resultado de Gemini no se interpreta como prueba de plagio, fraude o titularidad. El sistema lo presenta como una evaluación orientativa que debe complementarse con evidencia documental y revisión humana especializada.

# PROMPTS USADOS 

Fase 1. Planificación y arquitectura
Abre Gemini y pega este primer prompt.
PROMPT 1 — Analizar la actividad y diseñar la solución
Actúa como un ingeniero de software senior especializado en Python, APIs REST, pruebas unitarias y uso de Gemini API.
Necesito desarrollar un proyecto académico para la asignatura Calidad de Software con los siguientes requisitos:
Objetivo: desarrollar una API REST que consuma datos reales del Portal Nacional de Datos Abiertos de Colombia, integre Gemini para análisis inteligente, implemente pruebas unitarias y resuelva una problemática ética.
Problemática: disputa de patentes por falta de reconocimiento de la autoría real de un desarrollo.
Pregunta ética: ¿qué es más importante, la autoría o el lucro?
Requisitos obligatorios:
- Consumo de datos abiertos reales de Colombia.
- Integración con Gemini API.
- Endpoint funcional que analice un conflicto.
- Respuestas JSON.
- Pruebas unitarias con pytest.
- Validación de integridad de datos.
- Detección de inconsistencias.
- Uso de Gemini para evaluar la dimensión ética del conflicto.
Fuente de datos propuesta:
https://www.datos.gov.co/Comercio-Industria-y-Turismo/Patentes-publicadas/9n7g-3red
Tecnologías propuestas: Python, FastAPI, pytest, HTTPX o Requests y el SDK oficial de Gemini para Python.
Primero analiza los requisitos y entrégame:
1. Una explicación del problema que resolverá la aplicación.
2. Una arquitectura sencilla y adecuada para un estudiante.
3. Los endpoints necesarios y su propósito.
4. La estructura de carpetas y archivos.
5. Las reglas de validación de datos.
6. Los casos de prueba unitarios que deberíamos implementar.
7. El flujo de funcionamiento desde la petición hasta la respuesta JSON.
No escribas código todavía. No agregues tecnologías innecesarias. Distingue las inconsistencias técnicas de las posibles infracciones de propiedad intelectual y no presentes los resultados de la IA como pruebas legales.

Fase 2. Crear el proyecto en tu Mac
Cuando Gemini haya terminado la planificación, pídele que te guíe para preparar el entorno de Python.
PROMPT 2 — Preparar el entorno
Basándote en la arquitectura que acabas de proponer, guíame paso a paso para crear el proyecto en mi Mac.
Necesito que me indiques:
1. Cómo comprobar la versión de Python.
2. Cómo crear la carpeta del proyecto.
3. Cómo crear y activar un entorno virtual.
4. Qué dependencias instalar y para qué sirve cada una.
5. Cómo organizar las carpetas y archivos.
6. Cómo configurar de forma segura la clave de Gemini mediante variables de entorno.
7. Cómo ejecutar FastAPI y comprobar que funciona.
Dame comandos concretos para la terminal de macOS, uno por uno, y explícame qué resultado debería observar después de cada paso. No avances al siguiente paso hasta que pueda verificar el anterior. No expongas claves secretas en el código ni en GitHub.

Fase 3. Conectar los datos abiertos de Colombia
El portal utiliza identificadores de conjuntos de datos. Para las patentes publicadas, el identificador es 9n7g-3red.
El endpoint de consulta pública de Socrata tiene esta estructura:
https://www.datos.gov.co/resource/9n7g-3red.json?$limit=10


Esa URL sirve como punto de partida para obtener una muestra de registros. La respuesta esperada es un arreglo JSON con los datos disponibles.
PROMPT 3 — Implementar el consumo de datos
Implementemos ahora el módulo encargado de consumir los datos abiertos de patentes de Colombia.
Utiliza como fuente:
https://www.datos.gov.co/resource/9n7g-3red.json
Requisitos:
1. Crear una función que consulte la API pública.
2. Permitir buscar por número de solicitud.
3. Devolver los resultados como datos estructurados.
4. Manejar errores de conexión, respuestas HTTP fallidas y respuestas JSON inválidas.
5. Establecer tiempos de espera razonables.
6. No descargar innecesariamente todos los registros.
7. Separar el consumo HTTP de la lógica de validación.
8. Crear pruebas unitarias que simulen las respuestas HTTP para no depender de Internet durante cada prueba.
Antes de escribir código, confirma los nombres exactos de las columnas que necesitamos. Después implementa solamente este módulo y explícame cómo verificarlo.

Fase 4. Implementar las validaciones y las pruebas unitarias
Esta es la fase más importante para la asignatura.
La validación debe funcionar sin necesidad de llamar a Gemini. Así podrás demostrar que tus reglas de calidad son deterministas y comprobables.
PROMPT 4 — Validación de integridad y pytest
Implementa el módulo de validación de integridad para la API de patentes.
Crea reglas para comprobar:
- Existencia del número de solicitud.
- Título vacío o ausente.
- Inventor y solicitante ausentes.
- Año de publicación inválido o con tipo incorrecto.
- Identificadores de solicitud duplicados en un conjunto de registros.
- Registros incompletos y campos con tipos inesperados.
Requisitos de calidad:
1. Cada regla debe producir un resultado claro y verificable.
2. Distingue campos obligatorios, campos recomendados y anomalías.
3. No declares una infracción de autoría solo porque falte un campo.
4. Crea pruebas unitarias con pytest para casos válidos, inválidos y límites.
5. Usa datos de prueba ficticios, sin depender de la API pública.
6. Comprueba que cada prueba falle cuando corresponda y pase cuando se cumpla la regla.
Entrégame el código y después explícame cómo ejecutar las pruebas y cómo interpretar sus resultados. No continúes con Gemini todavía.

Fase 5. Integrar Gemini
Ahora sí, conecta el modelo. Gemini debe recibir un resumen de los hechos y las inconsistencias ya detectadas, no reemplazar las validaciones programadas.
PROMPT 5 — Análisis ético con Gemini API
Implementa el módulo de análisis ético utilizando el SDK oficial de Gemini para Python y la API key configurada mediante una variable de entorno.
El modelo debe evaluar casos hipotéticos o reales documentados de posibles disputas de autoría en el contexto de patentes.
Debe analizar:
1. Qué información verificable existe en los registros.
2. Qué inconsistencias fueron detectadas por el sistema.
3. Qué información falta para comprender el conflicto.
4. Qué riesgos éticos existen cuando no se reconoce una contribución.
5. La pregunta: ¿qué es más importante, la autoría o el lucro?
6. Qué pasos de verificación adicionales serían razonables.
La respuesta debe tener una estructura JSON consistente con campos como resumen, hechos_verificados, inconsistencias, informacion_faltante, analisis_etico y recomendaciones.
No permitas que Gemini invente datos, afirme culpabilidad sin pruebas o presente el registro de una patente como prueba definitiva de quién desarrolló una tecnología. El análisis debe ser neutral y reconocer las limitaciones de la información disponible.
Maneja errores de autenticación, límites de solicitudes, indisponibilidad del servicio y respuestas no válidas. Las pruebas unitarias deben simular la respuesta de Gemini; no deben consumir la API real ni depender de su disponibilidad.
Implementa solamente este módulo y explícame cómo probarlo.

Fase 6. Crear el endpoint principal
Cuando ambos módulos funcionen por separado, intégralos.
PROMPT 6 — Endpoint /analizar-conflicto
Integra el consumo de datos abiertos, la validación de integridad y el análisis de Gemini en el endpoint POST /analizar-conflicto.
El endpoint debe:
1. Recibir en JSON los identificadores de las solicitudes que se quieren comparar y una descripción del conflicto.
2. Validar el formato de entrada.
3. Consultar los registros reales disponibles.
4. Ejecutar las reglas deterministas de integridad.
5. Enviar a Gemini únicamente el contexto necesario para el análisis ético.
6. Devolver una respuesta JSON que contenga el estado de la operación, los registros encontrados, las inconsistencias, el análisis ético y las limitaciones.
7. Gestionar errores de entrada, ausencia de registros y fallos de servicios externos.
No supongas que dos patentes similares demuestran plagio. Si la evidencia no es suficiente, devuelve un resultado de información insuficiente.
Crea pruebas de integración con dependencias simuladas para verificar el flujo completo sin depender de Internet ni de la API real de Gemini.
Muestra un ejemplo de petición y otro de respuesta JSON. Explícame cómo probar el endpoint mediante la documentación interactiva de FastAPI.

Fase 7. Verificar la calidad del proyecto completo
No basta con que la API arranque. Necesitas evidencias de que funciona correctamente y que los fallos previsibles se manejan bien.
PROMPT 7 — Auditoría de calidad
Actúa como evaluador de calidad de software. Revisa todo el proyecto implementado sin reescribirlo de inmediato.
Comprueba:
- Que cada requisito de la actividad esté implementado.
- Que existan pruebas unitarias para las reglas de integridad.
- Que los módulos de datos y Gemini tengan errores controlados.
- Que las pruebas no dependan de Internet ni de llamadas reales a Gemini.
- Que los endpoints devuelvan JSON y códigos HTTP adecuados.
- Que las claves secretas no estén en el repositorio.
- Que se diferencien hechos verificados, inconsistencias y conclusiones generadas por IA.
- Que haya casos negativos y límites, no solamente pruebas exitosas.
Ejecuta o indícame cómo ejecutar la suite completa de pruebas. Identifica los problemas concretos, priorízalos y propón correcciones pequeñas. No declares que el proyecto está probado si no hay resultados verificables.
 Copiar prompt
