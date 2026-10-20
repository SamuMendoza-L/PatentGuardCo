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

La última ejecución de la suite produjo el siguiente resultado:

```text
18 passed
```

Se emitieron advertencias de deprecación de FastAPI/Pydantic; no provocan fallos funcionales, pero deben atenderse antes de una actualización mayor de las dependencias.

## Conclusión sobre el uso de Gemini

Gemini está justificado como una capa de apoyo cualitativo para organizar hallazgos, explicar limitaciones y formular recomendaciones relacionadas con la tensión entre autoría y lucro. La decisión técnica relevante no se delega a la IA: los campos obligatorios, la unicidad de las solicitudes, los tipos de datos y las fechas se evalúan mediante reglas de código comprobables.

Por esta razón, un resultado de Gemini no se interpreta como prueba de plagio, fraude o titularidad. El sistema lo presenta como una evaluación orientativa que debe complementarse con evidencia documental y revisión humana especializada.
